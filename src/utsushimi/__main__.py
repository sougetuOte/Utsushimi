"""起動：`pythonw.exe -m utsushimi`（design.md §1。主人の起動方法はこれを指すショートカット）。"""
import ctypes
import hashlib
import logging
import signal
import sys
import threading
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from . import DATA
from .core import Core
from .ui import ChatWindow, CreationWindow, ask_reseal, make_tray, notify_persona_broken

log = logging.getLogger("utsushimi")
WM_ENDSESSION = 0x0016
SESSION_END_WAIT = 4  # Windows がプロセスを止める前に、終了処理を待つ上限の秒数


def setup_logging():
    (DATA / "logs").mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(DATA / "logs" / "utsushimi.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s pid=%(process)d thread=%(threadName)s %(levelname)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    # SDK と HTTP の下回りは警告以上だけ
    for name in ("anthropic", "httpx", "httpx2", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    sys.excepthook = lambda t, v, tb: log.error("uncaught", exc_info=(t, v, tb))
    threading.excepthook = lambda a: log.error(
        "uncaught in %s", a.thread.name, exc_info=(a.exc_type, a.exc_value, a.exc_traceback))


def instance_name() -> str:
    """2重起動を見分ける名前。データの置き場ごとに1つ（確かめの置き場と本物の相棒は同時に動いてよい）。"""
    return "utsushimi-" + hashlib.sha256(str(DATA.resolve()).lower().encode()).hexdigest()[:16]


def ask_first_to_show(name: str) -> bool:
    """先に起動しているものがあれば「表示」を頼んで True（design.md §4.1 の 1）。"""
    sock = QLocalSocket()
    sock.connectToServer(name)
    if not sock.waitForConnected(500):
        return False
    sock.write(b"show")
    sock.waitForBytesWritten(500)
    sock.disconnectFromServer()
    return True


class SessionEnd(QAbstractNativeEventFilter):
    """Windows のサインアウト・シャットダウン（WM_ENDSESSION）で終了処理を呼び、終わるまで待つ。"""

    def __init__(self, core):
        super().__init__()
        self.core = core
        self.called = False

    def nativeEventFilter(self, event_type, message):
        msg = wintypes.MSG.from_address(int(message))
        if msg.message == WM_ENDSESSION and msg.wParam and not self.called:
            self.called = True  # WM_ENDSESSION は窓ごとに届くので、1回目だけ
            self.core.shutdown("session_end")
            self.core.done.wait(SESSION_END_WAIT)
        return False, 0


def main():
    setup_logging()
    threading.current_thread().name = "ui"
    console = "present" if ctypes.windll.kernel32.GetConsoleWindow() else "none"

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    name = instance_name()
    if ask_first_to_show(name):
        log.info("instance exists")  # 核を起こす前に終わる（DB にも lifecycle にも触れない）
        return
    QLocalServer.removeServer(name)  # 強制終了で残った名前を片づける
    server = QLocalServer()
    server.listen(name)
    core = Core(console)
    win = ChatWindow(core)
    creation = CreationWindow(core)
    tray = make_tray(win, core)

    def hide_all():
        win.hide()
        creation.hide()
        tray.hide()

    def ready(via):
        if via == "creation":  # 確定した：起動し直さずに会話の窓へ替わる
            creation.finish()
        tray.show()
        win.show_window(via)

    def second():
        """2つ目の起動に頼まれた：いま出ている画面を表に出す。"""
        conn = server.nextPendingConnection()
        conn.waitForReadyRead(500)
        conn.close()
        if creation.isVisible():
            creation.raise_()
            creation.activateWindow()
            log.info("show via=second")
        elif tray.isVisible():
            win.show_window("second")

    server.newConnection.connect(second)

    # コンソールから起動したときの Ctrl+C。Qt のイベントループの間も Python が合図を受け取れるように、時々起こす
    if console == "present":
        ctypes.windll.kernel32.SetConsoleCtrlHandler(None, False)  # 起動元が Ctrl+C を無視していても、それを継がない
    signal.signal(signal.SIGINT, lambda *_: core.shutdown("console"))
    wake = QTimer()
    wake.start(200)
    wake.timeout.connect(lambda: None)
    session_end = SessionEnd(core)
    app.installNativeEventFilter(session_end)

    s = core.signals
    s.persona_broken.connect(lambda lines: notify_persona_broken(core, lines))
    s.persona_ask.connect(lambda kind: ask_reseal(core, kind))
    s.ready.connect(ready)
    s.hide_all.connect(hide_all)
    s.finished.connect(app.quit)
    core.start()
    code = app.exec()
    core.thread.join(timeout=5)
    sys.exit(code)


main()
