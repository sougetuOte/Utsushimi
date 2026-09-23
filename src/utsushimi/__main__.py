"""起動：`pythonw.exe -m utsushimi`（design.md §1。主人の起動方法はこれを指すショートカット）。"""
import ctypes
import logging
import sys
import threading

from PySide6.QtWidgets import QApplication

from . import DATA
from .core import Core
from .ui import ChatWindow, make_tray

log = logging.getLogger("utsushimi")


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


def main():
    setup_logging()
    threading.current_thread().name = "ui"
    console = "present" if ctypes.windll.kernel32.GetConsoleWindow() else "none"

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    core = Core(console)
    win = ChatWindow(core)
    tray = make_tray(win, core)

    def hide_all():
        win.hide()
        tray.hide()

    core.signals.hide_all.connect(hide_all)
    core.signals.finished.connect(app.quit)
    core.start()
    tray.show()
    win.show_window("start")
    code = app.exec()
    core.thread.join(timeout=5)
    sys.exit(code)


main()
