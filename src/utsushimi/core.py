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

from PySide6.QtCore import QObject, Signal

from . import DATA, REPO
from .llm import Llm
from .memory import Memory

log = logging.getLogger("utsushimi")

HISTORY = 40  # 文脈に入れる直近の発言の数（文脈の組み方は T2・T4 で置き換える）


class CoreSignals(QObject):
    """核 → 画面。画面のスレッドで作るので、核から emit するとキュー接続で画面のスレッドに届く。"""
    loaded = Signal(list)            # [(speaker, body), ...]
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
        self.shutdown_calls = 0

    # ── 画面のスレッドから呼ぶ口（値だけを渡す） ──

    def start(self):
        self.thread.start()

    def submit(self, text: str):
        self.loop.call_soon_threadsafe(self._on_input, text)

    def shutdown(self, via: str):
        self.loop.call_soon_threadsafe(self._shutdown, via)

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
        self.signals.loaded.emit(rows)
        await self.stopped.wait()

    def _on_input(self, text: str):
        if self.shutdown_calls:
            return
        self.task = self.loop.create_task(self._converse(text))

    async def _converse(self, text: str):
        # 主人の発言は LLM より先にコミットする（ADR 0002・0004）
        uid = self.memory.add_utterance("master", text)
        log.info("send id=%d", uid)
        self.signals.said.emit("master", text)
        self.signals.reply_started.emit()
        try:
            body, stop = await self.llm.reply(self.memory.utterances(HISTORY), self.signals.reply_text.emit)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("reply failed")
            self.signals.reply_failed.emit(type(e).__name__)
            return
        if body is None:
            log.info("reply refused stop_reason=%s", stop)
            self.signals.reply_failed.emit("refusal")
            return
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
        self.memory.end_session(via)
        self.memory.close()
        log.info("shutdown done")
        self.signals.finished.emit()
        self.stopped.set()
