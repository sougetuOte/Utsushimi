"""核：asyncio のイベントループ1本を回すスレッド（ADR 0004）。

記憶（SQLite）と LLM のクライアントは核だけが持つ。画面とは値だけをやり取りする：
画面 → 核は `loop.call_soon_threadsafe`、核 → 画面は Qt のシグナル。
"""
import asyncio
import logging
import os
import shutil
import threading
import tomllib
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from . import DATA, REPO, persona
from .llm import Llm
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


class CoreSignals(QObject):
    """核 → 画面。画面のスレッドで作るので、核から emit するとキュー接続で画面のスレッドに届く。"""
    persona_broken = Signal(list)    # ["core.md の「C1」：見出しが無い", ...]
    persona_ask = Signal(str)        # changed / unsealed（主人に固め直すかを問う）
    loaded = Signal(list)            # [(speaker, body), ...]
    ready = Signal()                 # 会話の窓を出してよい
    said = Signal(str, str)          # speaker, body（保存を済ませてから出す）
    reply_started = Signal()
    reply_text = Signal(str)         # 届いた分
    reply_done = Signal()
    reply_failed = Signal(str)
    hide_all = Signal()
    finished = Signal()


def load_config() -> dict:
    path = DATA / "config.toml"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "config.default.toml", path)
    with path.open("rb") as f:
        return tomllib.load(f)


class Core:
    def __init__(self, console: str):
        self.console = console
        self.signals = CoreSignals()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, name="core", daemon=True)
        self.task = None
        self.persona = None
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

    # ── ここから下は核のスレッド ──

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.set_exception_handler(
            lambda loop, ctx: log.error("core %s", ctx.get("message"), exc_info=ctx.get("exception")))
        self.loop.run_until_complete(self._main())

    async def _main(self):
        self.stopped = asyncio.Event()
        config = load_config()
        self.memory = Memory(DATA / "utsushimi.db")
        prev = self.memory.begin_session(os.getpid())
        rows = self.memory.utterances()
        log.info("start console=%s prev_shutdown=%s loaded=%d", self.console, prev, len(rows))
        if prev == "unclean":
            log.info("前回は正しく終わらなかった")
        self.llm = Llm(config["llm"])
        if await self._load_persona():
            self.signals.loaded.emit(rows)
            self.signals.ready.emit()
            self.task = self.loop.create_task(self._greet())
        await self.stopped.wait()

    async def _load_persona(self) -> bool:
        """人格を読んで検査し、固めた値と比べる（design.md §4.1 の 3）。壊れていれば False。"""
        p = persona.Persona(PERSONA_DIR)
        if p.problems:
            lines = []
            for name, heading, reason in p.problems:
                log.info("persona broken file=%s heading=%s reason=%s", name, heading, reason)
                if heading == "-":
                    lines.append(f"{name}：ファイルが無い")
                else:
                    lines.append(f"{name} の「{heading}」：" + ("見出しが無い" if reason == "missing" else "中身が空"))
            self.signals.persona_broken.emit(lines)
            return False
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
        return True

    def _system(self) -> list[dict]:
        """文脈の前半。変わらない物を前に置き、見本までをキャッシュの区切りにする（design.md §4.2・ADR 0003）。"""
        now = datetime.now()
        return [
            {"type": "text", "text": INSTRUCTIONS},
            {"type": "text",
             "text": "# 人格の根っこ\n\n" + self.persona.texts["core.md"]
                     + "\n\n# 口調の見本（状況と発話の対）\n\n" + self.persona.texts["style.md"],
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": f"今は {now:%Y-%m-%d}（{WEEKDAYS[now.weekday()]}）{now:%H:%M} です。"},
        ]

    async def _call(self, kind: str, cue: str | None = None):
        """LLM を呼び、使用量をログに残す。失敗は画面に知らせて None を返す。"""
        self.signals.reply_started.emit()
        try:
            body, stop, usage = await self.llm.reply(
                self._system(), self.memory.utterances(HISTORY), self.signals.reply_text.emit, cue)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("%s failed", kind)
            self.signals.reply_failed.emit(type(e).__name__)
            return None
        log.info("usage kind=%s input=%d cache_read=%d cache_write=%d output=%d", kind, usage.input_tokens,
                 usage.cache_read_input_tokens or 0, usage.cache_creation_input_tokens or 0, usage.output_tokens)
        if body is None:
            log.info("%s refused stop_reason=%s", kind, stop)
            self.signals.reply_failed.emit("refusal")
            return None
        return body, stop

    async def _greet(self):
        """起動したら、キャラから最初のひと言（Bug-7：今の日時を文脈に入れる）。"""
        try:
            result = await self._call("greet", GREETING_CUE)
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
        result = await self._call("reply")
        if result is None:
            return
        body, stop = result
        rid = self.memory.add_utterance("companion", body)
        log.info("reply id=%d stop_reason=%s", rid, stop)
        self.signals.reply_done.emit()

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
        await self.llm.client.close()
        if self.persona:
            h = persona.hashes(PERSONA_DIR)
            log.info("persona at_exit core=%s style=%s", h.get("core.md"), h.get("style.md"))
        self.memory.end_session(via)
        self.memory.close()
        log.info("shutdown done")
        self.signals.finished.emit()
        self.stopped.set()
