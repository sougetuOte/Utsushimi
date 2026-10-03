"""核：asyncio のイベントループ1本を回すスレッド（ADR 0004）。

記憶（SQLite）と LLM のクライアントは核だけが持つ。画面とは値だけをやり取りする：
画面 → 核は `loop.call_soon_threadsafe`、核 → 画面は Qt のシグナル。
"""
import asyncio
import logging
import os
import random
import shutil
import threading
import tomllib
from collections import namedtuple
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from . import DATA, REPO, creation, llm, persona
from .memory import Memory

log = logging.getLogger("utsushimi")

HISTORY = 40  # 文脈に入れる直近の発言の数（上限と削る順は T4 で置き換える）
PERSONA_DIR = DATA / "persona"

# 文脈の 1：固定の指示（design.md §4.2）
INSTRUCTIONS = """あなたは主人のデスクトップに常駐する相棒です。下に書く「人格の根っこ」の人物として、日本語で主人と話します。
- 返事をする前に、このキャラならどう受け取り、どう反応するかを内心で踏まえてから話す。
- 気持ちや動作を括弧書き（「（嬉しそうに）」のような、括弧でくくったト書き）で書かない。気持ちは言葉づかいだけで表す。
- 口調の見本は手本であって台本ではない。見本の文をそのまま繰り返さない。
- チャット欄での会話なので、短く自然に話す。見出しや箇条書きは使わない。"""

GREETING_CUE = "起動の合図：主人が今、あなたを起動しました。今の日時に合った最初のひと言を、あなたから主人にかけてください。この合図のことには触れないでください。"
WEEKDAYS = "月火水木金土日"

Out = namedtuple("Out", "started text failed")  # 返事を流す先（会話の窓／お試し）


class CoreSignals(QObject):
    """核 → 画面。画面のスレッドで作るので、核から emit するとキュー接続で画面のスレッドに届く。"""
    persona_broken = Signal(list)    # ["core.md の「C1」：見出しが無い", ...]
    persona_ask = Signal(str)        # changed / unsealed（主人に固め直すかを問う）
    loaded = Signal(str, list)       # キャラの名前（C1）, [(speaker, body), ...]
    ready = Signal(str)              # 会話の窓を出してよい（via：start／creation）
    said = Signal(str, str)          # speaker, body（保存を済ませてから出す）
    reply_started = Signal()
    reply_text = Signal(str)         # 届いた分
    reply_done = Signal()
    reply_failed = Signal(str)
    creation_show = Signal()         # 人格が無い：キャラ作りの画面を出す（BH-06）
    creation_stage = Signal(str)     # 経過の表示
    creation_candidates = Signal(list)  # [(名前, 人格核文), ...]
    creation_trial = Signal(str)     # お試しの会話を始める（候補の名前）
    creation_failed = Signal(str)    # 失敗の理由。入力の画面へ戻る
    trial_said = Signal(str)         # お試しの主人の発言（保存を済ませてから出す）
    trial_started = Signal()
    trial_text = Signal(str)
    trial_done = Signal()
    trial_failed = Signal(str)
    hide_all = Signal()
    finished = Signal()


def load_config() -> dict:
    """設定。data/config.toml に無い項目は config.default.toml の値を使う（前の版で作った設定には新しい項目が無い）。"""
    path = DATA / "config.toml"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "config.default.toml", path)
    with (REPO / "config.default.toml").open("rb") as f:
        config = tomllib.load(f)
    with path.open("rb") as f:
        for section, values in tomllib.load(f).items():
            config.setdefault(section, {}).update(values)
    return config


class Core:
    def __init__(self, console: str):
        self.console = console
        self.signals = CoreSignals()
        s = self.signals
        self.chat_out = Out(s.reply_started, s.reply_text, s.reply_failed)
        self.trial_out = Out(s.trial_started, s.trial_text, s.trial_failed)
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, name="core", daemon=True)
        self.task = None
        self.persona = None
        self.draft = None      # 作りかけの人格（キャラ作りの間だけ）
        self.trial_index = None
        self.trial_after = 0   # この番号より後の trial の発言が、いまのお試しの会話
        self.shutdown_calls = 0

    # ── 画面のスレッドから呼ぶ口（値だけを渡す） ──

    def start(self):
        self.thread.start()

    def submit(self, text: str):
        self.loop.call_soon_threadsafe(self._on_input, text)

    def shutdown(self, via: str):
        self.loop.call_soon_threadsafe(self._shutdown, via)

    def answer_seal(self, reseal: bool):
        self.loop.call_soon_threadsafe(self.seal_answer.set_result, reseal)

    # キャラ作りの画面から（design.md §3・§4.3）
    def create(self, method: str, text: str):
        self.loop.call_soon_threadsafe(self._begin, self._create, method, text)

    def pick(self, index: int):
        self.loop.call_soon_threadsafe(self._begin, self._pick, index)

    def trial_send(self, text: str):
        self.loop.call_soon_threadsafe(self._begin, self._trial, text)

    def back(self):
        self.loop.call_soon_threadsafe(self._back)

    def redo(self):
        self.loop.call_soon_threadsafe(self._begin, self._redo)

    def confirm(self):
        self.loop.call_soon_threadsafe(self._begin, self._confirm)

    # ── ここから下は核のスレッド ──

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.set_exception_handler(
            lambda loop, ctx: log.error("core %s", ctx.get("message"), exc_info=ctx.get("exception")))
        self.loop.run_until_complete(self._main())

    async def _main(self):
        self.stopped = asyncio.Event()
        self.config = load_config()
        self.memory = Memory(DATA / "utsushimi.db")
        prev = self.memory.begin_session(os.getpid())
        rows = self.memory.utterances()
        log.info("start console=%s prev_shutdown=%s loaded=%d", self.console, prev, len(rows))
        if prev == "unclean":
            log.info("前回は正しく終わらなかった")
        target = self.config["llm"]["target"]
        self.llm = llm.make(self.config["llm"])
        # 核の乱数（禁則）：本番は OS の乱数で、種を持たない。種を読むのは呼び先が偽物のときだけ
        fake = target == "fake"
        self.rng = random.Random(self.config["creation"].get("seed", 0)) if fake else random.SystemRandom()
        log.info("llm target=%s rng source=%s", target, "fixed" if fake else "os")
        state = await self._load_persona()
        if state == "ok":
            self._open_chat("start")
        elif state == "absent":
            self.signals.creation_show.emit()
        await self.stopped.wait()

    async def _load_persona(self) -> str:
        """人格を読んで検査し、固めた値と比べる（design.md §4.1 の 3）。ok／absent／broken を返す。

        ファイルが無くても封の行があれば、固めた人格が消えた状態なので、キャラ作りにせず broken にする。
        """
        p = persona.Persona(PERSONA_DIR)
        if p.absent and self.memory.last_seal() is None:
            log.info("persona absent")
            return "absent"
        if p.problems:
            lines = []
            for name, heading, reason in p.problems:
                log.info("persona broken file=%s heading=%s reason=%s", name, heading, reason)
                if heading == "-":
                    lines.append(f"{name}：ファイルが無い")
                else:
                    lines.append(f"{name} の「{heading}」：" + ("見出しが無い" if reason == "missing" else "中身が空"))
            self.signals.persona_broken.emit(lines)
            return "broken"
        log.info("persona ok core=%s style=%s", p.hashes["core.md"], p.hashes["style.md"])
        seal = self.memory.last_seal()
        if seal != p.hashes:
            kind = "unsealed" if seal is None else "changed"
            log.info("persona %s", kind)
            self.seal_answer = self.loop.create_future()
            self.signals.persona_ask.emit(kind)
            if await self.seal_answer:
                self.memory.add_seal(p.hashes)
                log.info("persona resealed core=%s style=%s", p.hashes["core.md"], p.hashes["style.md"])
            else:
                log.info("persona kept")
        self.persona = p
        return "ok"

    def _open_chat(self, via: str):
        """会話の窓を出し、キャラから最初のひと言をかける（起動したときと、キャラ作りで確定したとき）。"""
        self.signals.loaded.emit(self.persona.name, self.memory.utterances())
        self.signals.ready.emit(via)
        self.task = self.loop.create_task(self._greet())

    def _system(self, texts: dict[str, str]) -> list[dict]:
        """文脈の前半。変わらない物を前に置き、見本までをキャッシュの区切りにする（design.md §4.2・ADR 0003）。"""
        now = datetime.now()
        return [
            {"type": "text", "text": INSTRUCTIONS},
            {"type": "text",
             "text": "# 人格の根っこ\n\n" + texts["core.md"] + "\n\n# 口調の見本（状況と発話の対）\n\n" + texts["style.md"],
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": f"今は {now:%Y-%m-%d}（{WEEKDAYS[now.weekday()]}）{now:%H:%M} です。"},
        ]

    async def _call(self, kind: str, texts: dict[str, str], history: list, out: Out, cue: str | None = None):
        """LLM を呼び、使用量をログに残す。失敗は out で画面に知らせて None を返す。"""
        out.started.emit()
        try:
            body, stop, usage = await self.llm.reply(self._system(texts), history, out.text.emit, cue)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("%s failed", kind)
            out.failed.emit(type(e).__name__)
            return None
        if usage:  # 偽物の呼び先は使用量を持たない
            llm.log_usage(kind, usage)
        if body is None:
            log.info("%s refused stop_reason=%s", kind, stop)
            out.failed.emit("refusal")
            return None
        return body, stop

    async def _greet(self):
        """起動したら、キャラから最初のひと言（Bug-7：今の日時を文脈に入れる）。"""
        try:
            result = await self._call("greet", self.persona.texts, self.memory.utterances(HISTORY), self.chat_out,
                                      GREETING_CUE)
        except asyncio.CancelledError:
            log.info("greet cancelled")
            raise
        if result:
            gid = self.memory.add_utterance("companion", result[0])
            log.info("greet id=%d stop_reason=%s", gid, result[1])
            self.signals.reply_done.emit()

    def _on_input(self, text: str):
        if self.shutdown_calls:
            return
        if self.task and not self.task.done():
            self.task.cancel()  # 主人の入力が最優先。挨拶の途中なら引く
        self.task = self.loop.create_task(self._converse(text))

    async def _converse(self, text: str):
        # 主人の発言は LLM より先にコミットする（ADR 0002・0004）
        uid = self.memory.add_utterance("master", text)
        log.info("send id=%d", uid)
        self.signals.said.emit("master", text)
        result = await self._call("reply", self.persona.texts, self.memory.utterances(HISTORY), self.chat_out)
        if result is None:
            return
        body, stop = result
        rid = self.memory.add_utterance("companion", body)
        log.info("reply id=%d stop_reason=%s", rid, stop)
        self.signals.reply_done.emit()

    # ── キャラ作り（design.md §4.3。BH-06〜BH-11・BH-41・BH-42） ──

    def _begin(self, job, *args):
        """キャラ作りの画面の操作から、核の仕事を1つ始める。終わりかけなら始めない。"""
        if not self.shutdown_calls:
            self.task = self.loop.create_task(job(*args))

    async def _create(self, method: str, text: str):
        self.draft = creation.Draft(method, text)
        log.info("creation begin method=%s", method)
        await self._generate()

    async def _redo(self):
        """作り直す：同じ入力のまま、段2（連想）からやり直す。"""
        log.info("creation redo")
        await self._generate()

    async def _generate(self):
        """段1〜4：連想を広げて核の乱数で選び、調べ、候補を作る。失敗したら入力の画面へ戻す。"""
        d, count = self.draft, self.config["creation"]["associations"]
        d.reset()
        stage = "associate"
        try:
            self.signals.creation_stage.emit("連想を広げています…")
            offered = await creation.associate(self.llm, self.rng, d, count)
            log.info("creation associations setting=%d offered=%d chosen=%d", count, offered, len(d.associations))
            stage = "search"
            creation.choose_words(self.rng, d)
            self.signals.creation_stage.emit("調べています：" + "、".join(d.words))
            await creation.research(self.llm, d)
            log.info("creation search words=%d queries=%d", len(d.words), d.searches)
            stage = "integrate"
            self.signals.creation_stage.emit("候補をまとめています…" if d.method == "omakase" else "人格の根っこを書いています…")
            await creation.integrate(self.llm, d)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._creation_failed(stage, e)
            return
        log.info("creation candidates n=%d", len(d.candidates))
        self._show_candidates()

    def _show_candidates(self):
        self.signals.creation_candidates.emit([(c["C1"], c["C4"]) for c in self.draft.candidates])

    def _creation_failed(self, stage: str, e: Exception):
        log.error("creation failed stage=%s reason=%s", stage, type(e).__name__, exc_info=e)
        self.signals.creation_failed.emit(type(e).__name__)

    async def _pick(self, index: int):
        """候補を選ぶ。その候補の口調の見本（段5）を作ってから、お試しの会話に入る（BH-08）。"""
        d = self.draft
        log.info("creation pick index=%d", index)
        if index not in d.styles:
            self.signals.creation_stage.emit("口調の見本を作っています…")
            try:
                await creation.style(self.llm, d, index)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._creation_failed("style", e)
                return
            log.info("creation style index=%d", index)
        self.trial_index, self.trial_after = index, self.memory.last_id()
        self.signals.creation_trial.emit(d.candidates[index]["C1"])

    async def _trial(self, text: str):
        """お試しの会話。本物の対話と同じ文脈の組み方で、発言は種類 trial で残す（確定した後の文脈には入れない）。"""
        uid = self.memory.add_utterance("master", text, "trial")
        log.info("trial send id=%d", uid)
        self.signals.trial_said.emit(text)
        d, i = self.draft, self.trial_index
        texts = {"core.md": creation.core_md(d, i), "style.md": creation.style_md(d, i)}
        history = self.memory.utterances(HISTORY, "trial", self.trial_after)
        result = await self._call("trial", texts, history, self.trial_out)
        if result is None:
            return
        rid = self.memory.add_utterance("companion", result[0], "trial")
        log.info("trial reply id=%d stop_reason=%s", rid, result[1])
        self.signals.trial_done.emit()

    def _back(self):
        """やり直す：同じ候補の並びに戻る。"""
        log.info("creation back")
        self._show_candidates()

    async def _confirm(self):
        """確定（BH-08・BH-19）：選んだ候補の人格を書いて固め、起動し直さずに会話の窓へ移る。"""
        d, i = self.draft, self.trial_index
        files = {"core.md": creation.core_md(d, i), "style.md": creation.style_md(d, i),
                 "origin.md": creation.origin_md(d, self.llm.model)}
        try:
            sealed = persona.seal(PERSONA_DIR, files, self.memory)
        except Exception as e:
            self._creation_failed("seal", e)
            return
        log.info("persona sealed core=%s style=%s", sealed["core.md"], sealed["style.md"])
        self.draft = None
        if await self._load_persona() == "ok":
            self._open_chat("creation")

    def _shutdown(self, via: str):
        """終了処理は核の中の1か所だけ。1回目だけが進む（design.md §4.8）。"""
        self.shutdown_calls += 1
        log.info("shutdown begin via=%s call=%d", via, self.shutdown_calls)
        if self.shutdown_calls > 1:
            log.info("shutdown already in progress")
            return
        self.signals.hide_all.emit()
        if self.task:
            self.task.cancel()
        self.loop.create_task(self._finish(via))

    async def _finish(self, via: str):
        if self.task:
            await asyncio.gather(self.task, return_exceptions=True)
        await self.llm.close()
        if self.persona:
            h = persona.hashes(PERSONA_DIR)
            log.info("persona at_exit core=%s style=%s", h.get("core.md"), h.get("style.md"))
        self.memory.end_session(via)
        self.memory.close()
        log.info("shutdown done")
        self.signals.finished.emit()
        self.stopped.set()
