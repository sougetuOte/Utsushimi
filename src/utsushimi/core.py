"""核：asyncio のイベントループ1本を回すスレッド（ADR 0004）。

記憶（SQLite）と LLM のクライアントは核だけが持つ。画面とは値だけをやり取りする：
画面 → 核は `loop.call_soon_threadsafe`、核 → 画面は Qt のシグナル。
"""
import asyncio
import logging
import os
import random
import re
import shutil
import threading
import time
import tomllib
from collections import namedtuple
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, Signal

from . import DATA, DATA_SOURCE, REPO, creation, llm, persona
from .memory import Memory

log = logging.getLogger("utsushimi")

HISTORY = 40  # お試しの会話で文脈に入れる直近の発言の数
WARM_DAYS = 5  # 文脈に入れる直近の日記の日数（design.md §4.1 の 5）
RECALL = 5     # 検索で引く昔の発言の数（design.md §4.2 の 2）
IDLE = 60      # 主人の入力が止んでから、行動予定の活性の計算を再開するまでの秒数（design.md §4.7）
DIARY_TIMEOUT = 60  # 終了のときの日記を待つ上限の秒数（design.md §4.6）
PERSONA_DIR = DATA / "persona"

# 文脈の 1：固定の指示（design.md §4.2）
INSTRUCTIONS = """あなたは主人のデスクトップに常駐する相棒です。下に書く「人格の根っこ」の人物として、日本語で主人と話します。
- 返事をする前に、このキャラならどう受け取り、どう反応するかを内心で踏まえてから話す。
- 気持ちや動作を括弧書き（「（嬉しそうに）」のような、括弧でくくったト書き）で書かない。気持ちは言葉づかいだけで表す。
- 口調の見本は手本であって台本ではない。見本の文をそのまま繰り返さない。
- チャット欄での会話なので、短く自然に話す。見出しや箇条書きは使わない。"""

GREETING_CUE = "起動の合図：主人が今、あなたを起動しました。今の日時に合った最初のひと言を、あなたから主人にかけてください。この合図のことには触れないでください。"
WEEKDAYS = "月火水木金土日"
DIARY_PROMPT = """次は {date} の、あなたと主人の会話です。

{lines}

この日の日記を、あなたの視点で5〜8文で書いてください。見出しや箇条書きは使わず、日記の本文だけを書いてください。"""

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
        self.done = threading.Event()  # 終了処理が終わった（Windows のセッション終了で画面のスレッドが待つ）
        self.loop_task = None  # メインループ（design.md §4.7）
        self.plan_task = None  # 行動予定「日付をまたいだら日記」の仕事
        self.plan_paused_until = 0.0

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
        self.started = datetime.now()
        h, m = self.config["memory"]["day_start"].split(":")
        self.day_offset = timedelta(hours=int(h), minutes=int(m))
        log.info("data dir=%s", DATA_SOURCE)
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
        log.info("warm n=%d", len(self.memory.diaries(self._today().isoformat(), WARM_DAYS)))
        self.task = self.loop.create_task(self._greet())
        if self.loop_task is None:
            self.loop_task = self.loop.create_task(self._main_loop())

    # ── 1日の区切り（design.md §4.6）。ある時刻は、その時刻から区切りの時刻を引いた日付の日に属する ──

    def _today(self):
        return (datetime.now() - self.day_offset).date()

    def _day_start(self, day) -> str:
        return (datetime.combine(day, datetime.min.time()) + self.day_offset).isoformat(timespec="milliseconds")

    # ── 文脈（design.md §4.2 の 2・3） ──

    def _persona_blocks(self, texts: dict[str, str]) -> list[dict]:
        """変わらない物を前に置き、見本までをキャッシュの区切りにする（ADR 0003）。"""
        return [
            {"type": "text", "text": INSTRUCTIONS},
            {"type": "text",
             "text": "# 人格の根っこ\n\n" + texts["core.md"] + "\n\n# 口調の見本（状況と発話の対）\n\n" + texts["style.md"],
             "cache_control": {"type": "ephemeral"}},
        ]

    def _system(self, texts: dict[str, str], memory: str = "") -> list[dict]:
        now = datetime.now()
        blocks = self._persona_blocks(texts)
        if memory:
            blocks.append({"type": "text", "text": memory})
        blocks.append({"type": "text", "text": f"今は {now:%Y-%m-%d}（{WEEKDAYS[now.weekday()]}）{now:%H:%M} です。"})
        return blocks

    def _memory_text(self, diaries: list, recalled: list) -> str:
        """文脈の 4：直近の日記（Warm）と、検索で引いた昔の発言（Cold）。"""
        parts = []
        if diaries:
            parts.append("# 直近の日記（あなたが書いたもの）\n\n" + "\n\n".join(f"## {d}\n{body}" for d, body in diaries))
        if recalled:
            name = self.persona.name
            parts.append("# 思い出した昔の会話\n\n" + "\n".join(
                f"- {at[:10]} {'主人' if speaker == 'master' else name}：{body}" for _, at, speaker, body in recalled))
        return "\n\n".join(parts)

    def _context(self, kind: str, text: str | None = None, cue: str | None = None):
        """文脈を組み、上限を超えたら昔の発言 → 日記 → 今日の会話の古い方の順に削る（BH-17）。(system, history) を返す。

        固定の指示・人格の根っこ・口調の見本と、主人の最後の発言（返事のとき）は削らない。
        """
        today = self._today()
        start = self._day_start(today)
        diaries = self.memory.diaries(today.isoformat(), WARM_DAYS)
        query = _recall_query(text) if text else ""
        recalled = self.memory.recall(query, start, RECALL) if query else []
        if kind == "reply":
            log.info("recall ids=%s", ",".join(str(r[0]) for r in recalled) or "-")
        talk = self.memory.since(start)
        keep = 1 if kind == "reply" else 0
        limit = self.config["context"]["limit"]
        fixed = sum(len(b["text"]) for b in self._system(self.persona.texts))

        def size():
            return fixed + len(self._memory_text(diaries, recalled)) + sum(len(r[2]) for r in talk) + len(cue or "")

        cuts = {"recall": [0, 0], "diary": [0, 0], "today": [0, 0]}
        while size() > limit:
            if recalled:
                part, body = "recall", recalled.pop(0)[3]
            elif diaries:
                part, body = "diary", diaries.pop(0)[1]
            elif len(talk) > keep:
                part, body = "today", talk.pop(0)[2]
            else:
                break
            cuts[part][0] += 1
            cuts[part][1] += len(body)
        for part, (n, chars) in cuts.items():
            if n:
                log.info("context cut part=%s n=%d chars=%d", part, n, chars)
        total = size()
        if total > limit:
            log.info("context over limit=%d total=%d", limit, total)
        log.info("context kind=%s limit=%d total=%d fixed=%d recall=%d diary=%d today=%d",
                 kind, limit, total, fixed, len(recalled), len(diaries), len(talk))
        return self._system(self.persona.texts, self._memory_text(diaries, recalled)), [r[1:] for r in talk]

    async def _call(self, kind: str, system: list[dict], history: list, out: Out, cue: str | None = None):
        """LLM を呼び、使用量をログに残す。失敗は out で画面に知らせて None を返す。"""
        out.started.emit()
        try:
            body, stop, usage = await self.llm.reply(system, history, out.text.emit, cue)
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
            system, history = self._context("greet", cue=GREETING_CUE)
            result = await self._call("greet", system, history, self.chat_out, GREETING_CUE)
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
        self.plan_paused_until = time.monotonic() + IDLE  # 入力が止むまで、行動予定は活性にならない
        if self.task and not self.task.done():
            self.task.cancel()  # 主人の入力が最優先。挨拶の途中なら引く
        self.task = self.loop.create_task(self._converse(text))

    async def _converse(self, text: str):
        # 主人の発言は LLM より先にコミットする（ADR 0002・0004）。行動予定を引くのはその後（design.md §4.2 の 1）
        uid = self.memory.add_utterance("master", text)
        await self._cancel_plan("input")
        log.info("send id=%d", uid)
        self.signals.said.emit("master", text)
        system, history = self._context("reply", text)
        result = await self._call("reply", system, history, self.chat_out)
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
        result = await self._call("trial", self._system(texts), history, self.trial_out)
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

    # ── メインループと行動予定（design.md §4.7。保護指定2） ──

    async def _main_loop(self):
        """1秒ごとに行動予定の活性を計算し、活性なら仕事を始める。止まらない。活性の計算に LLM を呼ばない（BH-26）。"""
        day = self._today()
        paused = False
        while True:
            await asyncio.sleep(1)
            today = self._today()
            if today != day:
                day = today
                log.info("day change to=%s", day)
            if time.monotonic() < self.plan_paused_until:
                paused = True
                continue
            if paused:
                paused = False
                log.info("plan resume")
            if self.plan_task and not self.plan_task.done():
                continue
            # 行動予定「日付をまたいだら日記」：今日より前で、発言があって日記の無い日
            date = self.memory.missing_diary(_shift(self.day_offset), self._day_start(today))
            if date:
                log.info("plan active name=diary date=%s", date)
                end = datetime.fromisoformat(self._day_start(datetime.fromisoformat(date).date() + timedelta(days=1)))
                trigger = "startup" if end <= self.started else "daychange"
                self.plan_task = self.loop.create_task(self._write_diary(date, trigger))

    async def _cancel_plan(self, reason: str):
        """すべての行動予定を非活性に戻し、走っている仕事を止める（design.md §4.2 の 1）。"""
        if self.plan_task and not self.plan_task.done():
            log.info("plan inactive name=diary reason=%s", reason)
            t0 = time.monotonic()
            self.plan_task.cancel()
            await asyncio.gather(self.plan_task, return_exceptions=True)
            log.info("plan cancel name=diary ms=%d", (time.monotonic() - t0) * 1000)

    async def _write_diary(self, date: str, trigger: str):
        """1日分の dialogue の発言から、キャラの視点で日記を書いて足す（BH-15）。"""
        day = datetime.fromisoformat(date).date()
        rows = self.memory.since(self._day_start(day), self._day_start(day + timedelta(days=1)))
        name = self.persona.name
        lines = "\n".join(f"{'主人' if speaker == 'master' else name}：{body}" for _, speaker, body in rows)
        try:
            body = await self.llm.text("diary", self._persona_blocks(self.persona.texts),
                                       DIARY_PROMPT.format(date=date, lines=lines))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error("diary failed date=%s reason=%s", date, type(e).__name__, exc_info=e)
            self.plan_paused_until = time.monotonic() + IDLE  # 続けて呼び直さない
            return
        if self.memory.add_diary(date, body):
            log.info("diary created date=%s trigger=%s", date, trigger)
        else:
            log.info("diary exists date=%s", date)

    async def _shutdown_diary(self):
        """終了のとき、窓とトレイを消した後で今日の日記を書く。上限を超えたら書かずに終える（design.md §4.6）。"""
        if not self.persona:
            return
        today = self._today()
        date = today.isoformat()
        if not self.memory.since(self._day_start(today)):
            return
        if self.memory.has_diary(date):
            log.info("diary exists date=%s", date)
            return
        try:
            await asyncio.wait_for(self._write_diary(date, "shutdown"), DIARY_TIMEOUT)
        except TimeoutError:
            log.info("diary timeout date=%s", date)

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
        for task in (self.loop_task, self.plan_task):
            if task:
                task.cancel()
        await asyncio.gather(*(t for t in (self.task, self.loop_task, self.plan_task) if t), return_exceptions=True)
        if via == "session_end":
            log.info("diary skipped reason=session_end")  # Windows が待つのは数秒なので書かない（design.md §4.8）
        else:
            await self._shutdown_diary()
        await self.llm.close()
        if self.persona:
            h = persona.hashes(PERSONA_DIR)
            log.info("persona at_exit core=%s style=%s", h.get("core.md"), h.get("style.md"))
        self.memory.end_session(via)
        self.memory.close()
        log.info("shutdown done")
        self.done.set()
        self.signals.finished.emit()
        self.stopped.set()


def _shift(offset: timedelta) -> str:
    """発言の時刻から1日の区切りを引く SQLite の修飾子。"""
    return f"-{int(offset.total_seconds() // 60)} minutes"


def _recall_query(text: str) -> str:
    """検索語：主人の入力の、空白と記号を含まない3文字の切れ目をすべて OR でつなぐ（trigram）。3文字に満たなければ空。"""
    grams = dict.fromkeys(run[i:i + 3] for run in re.findall(r"\w{3,}", text) for i in range(len(run) - 2))
    return " OR ".join(f'"{g}"' for g in grams)
