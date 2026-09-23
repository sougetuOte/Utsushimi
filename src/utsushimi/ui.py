"""画面：会話の窓とトレイ（design.md §3）。画面のスレッドだけで動き、核とは値だけをやり取りする。"""
import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap, QTextCursor
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox, QPushButton,
                               QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget)

from . import DATA

log = logging.getLogger("utsushimi")

EDGE = 8  # 外周の縁（ヘリ）。突っつきは T7 で足す
NAMES = {"master": "あなた", "companion": "Utsushimi"}


class Bar(QWidget):
    """上の帯。押してドラッグすると窓が動く（BH-02）。"""

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.window().windowHandle().startSystemMove()


class ChatWindow(QWidget):
    def __init__(self, core):
        super().__init__()
        self.core = core
        self.busy = False
        self.setWindowTitle("Utsushimi")
        # 枠なし、タスクバーに出さない（Qt のツール窓。入口はトレイ。BH-03）
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.resize(570, 390)
        self.setObjectName("chat")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "#chat{background:#2b2b33;} QLabel{color:#ddd;}"
            "QTextEdit,QLineEdit{background:#1f1f25;color:#eee;border:1px solid #444;}"
            "QPushButton{background:#3a3a45;color:#eee;border:1px solid #555;padding:2px 8px;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(EDGE + 4, EDGE, EDGE + 4, EDGE + 4)
        bar = Bar()
        row = QHBoxLayout(bar)
        row.setContentsMargins(4, 0, 0, 0)
        row.addWidget(QLabel("Utsushimi"), 1)
        close = QPushButton("×")
        close.setFixedSize(24, 24)
        close.clicked.connect(lambda: self.hide_window("close"))
        row.addWidget(close)
        root.addWidget(bar)

        self.transcript = QTextEdit(readOnly=True)
        self.transcript.setFocusPolicy(Qt.NoFocus)
        root.addWidget(self.transcript, 1)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.returnPressed.connect(self.send)
        row.addWidget(self.input, 1)
        self.send_button = QPushButton("送信")
        self.send_button.clicked.connect(self.send)
        row.addWidget(self.send_button)
        root.addLayout(row)

        s = core.signals
        s.loaded.connect(self.on_loaded)
        s.said.connect(self.append_line)
        s.reply_started.connect(self.on_reply_started)
        s.reply_text.connect(self.on_reply_text)
        s.reply_done.connect(self.on_reply_done)
        s.reply_failed.connect(self.on_reply_failed)

    # ── 窓の出し入れ ──

    def closeEvent(self, e):  # Alt+F4 も隠すだけ。終了はトレイから
        e.ignore()
        self.hide_window("close")

    def hide_window(self, via):
        self.hide()
        log.info("hide via=%s", via)

    def show_window(self, via):
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()
        log.info("show via=%s", via)

    # ── 会話 ──

    def send(self):
        text = self.input.text().strip()
        if not text or self.busy:
            return
        self.input.clear()
        self.busy = True
        self.send_button.setEnabled(False)
        self.core.submit(text)

    def append_line(self, speaker, body):
        self.transcript.append(f"{NAMES[speaker]}：{body}")

    def on_loaded(self, rows):
        for speaker, body in rows:
            self.append_line(speaker, body)

    def on_reply_started(self):
        self.transcript.append(f"{NAMES['companion']}：")

    def on_reply_text(self, text):
        cursor = self.transcript.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.transcript.ensureCursorVisible()

    def on_reply_done(self):
        self.busy = False
        self.send_button.setEnabled(True)

    def on_reply_failed(self, reason):
        self.on_reply_text(f"（うまく返せなかった：{reason}）")
        self.on_reply_done()


def notify_persona_broken(core, lines):
    """人格のファイルが壊れている（BH-25）。閉じたら終わる。"""
    box = QMessageBox(QMessageBox.Critical, "Utsushimi", "人格のファイルが壊れているため、起動を止めます。",
                      QMessageBox.Close)
    box.setInformativeText("\n".join(lines) + f"\n\n直してから、もう一度起動してください。\n場所：{DATA / 'persona'}")
    box.exec()
    core.shutdown("persona_broken")


def ask_reseal(core, kind):
    """固めた時から変わっている／まだ固めていない（BH-21）。固め直すかは主人が選ぶ。"""
    text = ("人格のファイル（core.md・style.md）が、固めた時から変わっています。" if kind == "changed"
            else "人格のファイル（core.md・style.md）は、まだ固められていません。")
    box = QMessageBox(QMessageBox.Question, "Utsushimi", text)
    box.setInformativeText("この内容で固め直すと、次の起動からは知らせません。")
    reseal = box.addButton("この内容で固め直す", QMessageBox.AcceptRole)
    box.addButton("このまま使う", QMessageBox.RejectRole)
    box.exec()
    core.answer_seal(box.clickedButton() is reseal)


def make_tray(win, core):
    pm = QPixmap(32, 32)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#7aa2f7"))
    p.setPen(Qt.NoPen)
    p.drawEllipse(2, 2, 28, 28)
    p.end()

    tray = QSystemTrayIcon(QIcon(pm))
    tray.setToolTip("Utsushimi")
    menu = QMenu()
    menu.addAction(QAction("表示", menu, triggered=lambda: win.show_window("tray")))
    menu.addAction(QAction("隠す", menu, triggered=lambda: win.hide_window("tray")))
    menu.addSeparator()
    menu.addAction(QAction("終了", menu, triggered=lambda: core.shutdown("tray")))
    tray.setContextMenu(menu)

    def toggle(reason):
        if reason == QSystemTrayIcon.Trigger:
            win.hide_window("tray") if win.isVisible() else win.show_window("tray")

    tray.activated.connect(toggle)
    return tray
