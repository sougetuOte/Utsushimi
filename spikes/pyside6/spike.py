"""Phase 1 スパイク：PySide6（Qt）。使い捨て。本体に持ち込まない。

共通の約束は spikes/README.md。
"""
import argparse
import ctypes
import os
import sqlite3
import sys
import threading
import time
from datetime import datetime

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QIcon, QPixmap, QColor
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPushButton, QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget)

TITLE = "utsushimi-spike-pyside6"
EDGE = 8
BAR = 28

p = argparse.ArgumentParser()
p.add_argument("--run-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "run"))
p.add_argument("--auto-send")
p.add_argument("--bg-seconds", type=float, default=3.0)
p.add_argument("--topmost", action="store_true")
args = p.parse_args()
os.makedirs(args.run_dir, exist_ok=True)
LOG = open(os.path.join(args.run_dir, "spike.log"), "a", encoding="utf-8", buffering=1)


def log(msg):
    LOG.write(f"{datetime.now().isoformat(timespec='milliseconds')} {msg}\n")


db = sqlite3.connect(os.path.join(args.run_dir, "spike.db"), check_same_thread=False)
db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA synchronous=FULL")
db.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, role TEXT, text TEXT, ts TEXT)")
db.commit()


def persist(role, text):
    cur = db.execute("INSERT INTO messages(role, text, ts) VALUES(?,?,?)",
                     (role, text, datetime.now().isoformat()))
    db.commit()
    return cur.lastrowid


class Win(QWidget):
    bg_done = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(TITLE)
        flags = Qt.FramelessWindowHint | Qt.Window
        if args.topmost:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.resize(380, 260)
        self.setStyleSheet("Win{background:#2b2b33;} QLabel{color:#ddd;}")
        self.setAttribute(Qt.WA_StyledBackground, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(EDGE + 4, EDGE, EDGE + 4, EDGE + 4)
        bar = QHBoxLayout()
        self.title = QLabel("相棒（spike）")
        bar.addWidget(self.title, 1)
        close = QPushButton("×")
        close.setFixedSize(22, 22)
        close.clicked.connect(self.hide_to_tray)
        bar.addWidget(close)
        root.addLayout(bar)
        self.transcript = QTextEdit(readOnly=True)
        self.transcript.setFocusPolicy(Qt.NoFocus)
        root.addWidget(self.transcript, 1)
        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.returnPressed.connect(self.send)
        row.addWidget(self.input, 1)
        send = QPushButton("送信")
        send.clicked.connect(self.send)
        row.addWidget(send)
        root.addLayout(row)

        self.bg_done.connect(self.on_bg_done)
        self.busy = False
        self.last_tick = 0.0
        self.max_gap = 0.0
        self.ticker = QTimer(self, interval=20)
        self.ticker.timeout.connect(self.tick)
        self.move_timer = QTimer(self, singleShot=True, interval=300)
        self.move_timer.timeout.connect(lambda: log(f"rect {self.rect_str()}"))

        rows = db.execute("SELECT role, text FROM messages ORDER BY id").fetchall()
        for role, text in rows:
            self.transcript.append(f"{role}: {text}")
        self.loaded = len(rows)

    def rect_str(self):
        g = self.frameGeometry()
        return f"{g.x()} {g.y()} {g.width()} {g.height()}"

    def moveEvent(self, e):
        self.move_timer.start()
        super().moveEvent(e)

    def closeEvent(self, e):  # Alt+F4 もトレイへ
        e.ignore()
        self.hide_to_tray()

    def hide_to_tray(self):
        self.hide()
        log("hide")

    def show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()
        log("show")

    def press(self, gpos, obj):
        lp = self.mapFromGlobal(gpos)
        x, y, w, h = lp.x(), lp.y(), self.width(), self.height()
        if x < EDGE or y < EDGE or x >= w - EDGE or y >= h - EDGE:
            log(f"poke edge {x} {y}")
            return True
        log(f"click inner {x} {y}")
        if y < EDGE + BAR and not isinstance(obj, QPushButton):
            self.windowHandle().startSystemMove()
            return True
        return False

    def send(self):
        text = self.input.text().strip()
        if not text or self.busy:
            return
        self.input.clear()
        rid = persist("user", text)
        log(f"send id={rid}")
        self.transcript.append(f"user: {text}")
        self.busy = True
        self.max_gap = 0.0
        self.last_tick = time.perf_counter()
        self.ticker.start()
        log("bg start")
        threading.Thread(target=self.work, daemon=True).start()

    def work(self):  # LLM 呼び出しの代わりの待ち
        time.sleep(args.bg_seconds)
        self.bg_done.emit()

    def tick(self):
        now = time.perf_counter()
        self.max_gap = max(self.max_gap, now - self.last_tick)
        self.last_tick = now

    def on_bg_done(self):
        self.ticker.stop()
        rid = persist("assistant", "（返事）")
        self.transcript.append("assistant: （返事）")
        self.busy = False
        log(f'bg end maxgap={self.max_gap * 1000:.0f}ms input_during_bg="{self.input.text()}"')
        log(f"reply id={rid}")


class Filter(QObject):
    def __init__(self, win):
        super().__init__()
        self.win = win

    def eventFilter(self, obj, e):
        if e.type() == QEvent.MouseButtonPress and isinstance(obj, QWidget) and obj.window() is self.win:
            return self.win.press(e.globalPosition().toPoint(), obj)
        return False


app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)
win = Win()
filt = Filter(win)
app.installEventFilter(filt)

pm = QPixmap(16, 16)
pm.fill(QColor("#7aa2f7"))
tray = QSystemTrayIcon(QIcon(pm))
tray.setToolTip(TITLE)
menu = QMenu()
menu.addAction(QAction("表示", menu, triggered=win.show_from_tray))
menu.addAction(QAction("終了", menu, triggered=app.quit))
tray.setContextMenu(menu)
tray.activated.connect(lambda r: win.show_from_tray() if r == QSystemTrayIcon.Trigger else None)
tray.show()

shutdowns = 0


def on_quit():
    global shutdowns
    shutdowns += 1
    log(f"shutdown count={shutdowns}")
    db.close()


app.aboutToQuit.connect(on_quit)

console = "present" if ctypes.windll.kernel32.GetConsoleWindow() else "none"
win.show()
win.input.setFocus()
log(f"start pid={os.getpid()} console={console} loaded={win.loaded} tray={QSystemTrayIcon.isSystemTrayAvailable()}")
log(f"rect {win.rect_str()}")
if args.auto_send:
    win.input.setText(args.auto_send)
    QTimer.singleShot(200, win.send)
sys.exit(app.exec())
