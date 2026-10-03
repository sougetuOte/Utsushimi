"""画面：会話の窓・キャラ作りの画面・トレイ（design.md §3）。画面のスレッドだけで動き、核とは値だけをやり取りする。"""
import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap, QTextCursor
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu, QMessageBox, QPlainTextEdit,
                               QProgressBar, QPushButton, QRadioButton, QScrollArea, QStackedWidget,
                               QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget)

from . import DATA

log = logging.getLogger("utsushimi")

EDGE = 8  # 外周の縁（ヘリ）。突っつきは T7 で足す
NAMES = {"master": "あなた", "companion": "Utsushimi"}  # キャラの名前は人格を読んだら C1 に替える
METHOD_HINTS = {
    "omakase": "キーワードを2〜3個（例：元気、歴史好き、朝型）",
    "image": "ほしい相棒を自由に書いてください。名前・一人称・あなたの呼び方・性格・口調などは、"
             "書いた所をそのまま使い、書いていない所を AI が補います。",
}


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
        self.names = dict(NAMES)
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
        self.transcript.append(f"{self.names[speaker]}：{body}")

    def on_loaded(self, name, rows):
        self.names["companion"] = name
        for speaker, body in rows:
            self.append_line(speaker, body)

    def on_reply_started(self):
        self.transcript.append(f"{self.names['companion']}：")

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


class CreationWindow(QWidget):
    """キャラ作りの画面（design.md §3・§4.3。BH-06〜BH-09・BH-42）。人格が無いとき、会話の窓の代わりに出る。

    枠のある普通の窓で、閉じるとアプリが終わる。確定したら隠れ、同じプロセスのまま会話の窓に替わる。
    場面は 0 方式と入力 → 1 経過 → 2 候補 → 3 お試し。
    """

    def __init__(self, core):
        super().__init__()
        self.core = core
        self.done = False
        self.name = ""
        self.trial_busy = False
        self.setWindowTitle("Utsushimi：キャラ作り")
        self.resize(640, 560)
        self.setObjectName("creation")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "#creation{background:#2b2b33;} QLabel,QRadioButton{color:#ddd;}"
            "QTextEdit,QLineEdit,QPlainTextEdit{background:#1f1f25;color:#eee;border:1px solid #444;}"
            "QPushButton{background:#3a3a45;color:#eee;border:1px solid #555;padding:4px 10px;}"
            "QPushButton:disabled{color:#777;} #card{border:1px solid #555;}"
            "QScrollArea,#cards{background:transparent;border:none;}")
        self.pages = QStackedWidget()
        QVBoxLayout(self).addWidget(self.pages)
        for page in (self._input_page(), self._progress_page(), self._candidates_page(), self._trial_page()):
            self.pages.addWidget(page)

        s = core.signals
        s.creation_show.connect(self.show_window)
        s.creation_stage.connect(self.on_stage)
        s.creation_candidates.connect(self.on_candidates)
        s.creation_trial.connect(self.on_trial)
        s.creation_failed.connect(self.on_failed)
        s.trial_said.connect(lambda text: self.trial.append(f"あなた：{text}"))
        s.trial_started.connect(lambda: self.trial.append(f"{self.name}："))
        s.trial_text.connect(self.on_trial_text)
        s.trial_done.connect(lambda: self.set_trial_busy(False))
        s.trial_failed.connect(self.on_trial_failed)

    # ── 場面 ──

    def _input_page(self):
        page = QWidget()
        col = QVBoxLayout(page)
        col.addWidget(QLabel("あなたの相棒を生みます。作り方を選んでください。"))
        self.omakase = QRadioButton("おまかせ：キーワードから、AI が調べながら候補を3体考えます")
        self.image = QRadioButton("既存イメージ：ほしい相棒を自由に書くと、AI が整えて足りない所を補います")
        self.omakase.setChecked(True)
        for button in (self.omakase, self.image):
            button.toggled.connect(self.on_method)
            col.addWidget(button)
        self.text = QPlainTextEdit()
        self.text.setAccessibleName("入力")
        col.addWidget(self.text, 1)
        self.error = QLabel(wordWrap=True)
        self.error.setStyleSheet("color:#f7768e;")
        self.error.hide()
        col.addWidget(self.error)
        row = QHBoxLayout()
        row.addStretch(1)
        make = QPushButton("作る")
        make.clicked.connect(self.make)
        row.addWidget(make)
        col.addLayout(row)
        self.on_method()
        return page

    def _progress_page(self):
        page = QWidget()
        col = QVBoxLayout(page)
        col.addStretch(1)
        self.stage = QLabel(alignment=Qt.AlignCenter, wordWrap=True)
        col.addWidget(self.stage)
        bar = QProgressBar(textVisible=False)
        bar.setRange(0, 0)  # 終わりの見えない待ち
        col.addWidget(bar)
        col.addStretch(1)
        return page

    def _candidates_page(self):
        page = QWidget()
        col = QVBoxLayout(page)
        col.addWidget(QLabel("候補です。話してみたい子を選んでください。"))
        holder = QWidget(objectName="cards")
        self.cards = QVBoxLayout(holder)
        scroll = QScrollArea(widgetResizable=True)
        scroll.setWidget(holder)
        col.addWidget(scroll, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel("どの子も違うと感じたら、同じ入力のまま連想から作り直せます。", wordWrap=True), 1)
        redo = QPushButton("作り直す")
        redo.clicked.connect(self.redo)
        row.addWidget(redo)
        col.addLayout(row)
        return page

    def _trial_page(self):
        page = QWidget()
        col = QVBoxLayout(page)
        self.trial_title = QLabel()
        self.trial_title.setStyleSheet("font-size:13pt;")
        col.addWidget(self.trial_title)
        col.addWidget(QLabel("確定すると、この子があなたの相棒になります。確定した後の根っこは、AI には書き換えられません。",
                             wordWrap=True))
        self.trial = QTextEdit(readOnly=True)
        self.trial.setFocusPolicy(Qt.NoFocus)
        col.addWidget(self.trial, 1)
        row = QHBoxLayout()
        self.trial_input = QLineEdit()
        self.trial_input.setAccessibleName("お試しの入力")
        self.trial_input.returnPressed.connect(self.trial_send)
        row.addWidget(self.trial_input, 1)
        self.send_button = QPushButton("送信")
        self.send_button.clicked.connect(self.trial_send)
        row.addWidget(self.send_button)
        col.addLayout(row)
        row = QHBoxLayout()
        self.back_button = QPushButton("やり直す")
        self.back_button.setToolTip("候補の並びに戻ります")
        self.back_button.clicked.connect(self.core.back)
        row.addWidget(self.back_button)
        row.addStretch(1)
        self.confirm_button = QPushButton("確定")
        self.confirm_button.clicked.connect(self.confirm)
        row.addWidget(self.confirm_button)
        col.addLayout(row)
        return page

    # ── 窓の出し入れ ──

    def show_window(self):
        self.pages.setCurrentIndex(0)
        self.show()
        self.raise_()
        self.activateWindow()
        self.text.setFocus()
        log.info("creation show")

    def finish(self):
        """確定した。閉じても終わらないようにしてから隠す。"""
        self.done = True
        self.hide()

    def closeEvent(self, e):
        if not self.done:
            self.core.shutdown("creation_close")
        e.accept()

    # ── 主人の操作と、核からの知らせ ──

    def method(self):
        return "omakase" if self.omakase.isChecked() else "image"

    def on_method(self):
        self.text.setPlaceholderText(METHOD_HINTS[self.method()])

    def make(self):
        text = self.text.toPlainText().strip()
        if not text:
            self.show_error("キーワードか記述を入れてください。")
            return
        self.error.hide()
        self.on_stage("始めています…")
        self.core.create(self.method(), text)

    def show_error(self, text):
        self.error.setText(text)
        self.error.show()

    def on_stage(self, text):
        self.stage.setText(text)
        self.pages.setCurrentIndex(1)

    def on_failed(self, reason):
        """生成の途中で失敗した。入れた言葉は残したまま、入力の画面へ戻す。"""
        self.show_error(f"うまく作れませんでした（{reason}）。入力を見直して、もう一度「作る」を押してください。")
        self.pages.setCurrentIndex(0)

    def on_candidates(self, candidates):
        while self.cards.count():
            item = self.cards.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, (name, statement) in enumerate(candidates):
            card = QFrame(objectName="card")
            col = QVBoxLayout(card)
            title = QLabel(name)
            title.setStyleSheet("font-size:15pt;")
            col.addWidget(title)
            col.addWidget(QLabel(statement, wordWrap=True))
            row = QHBoxLayout()
            row.addStretch(1)
            talk = QPushButton("この子と話してみる")
            talk.setAccessibleName(f"候補{i + 1}と話してみる")
            talk.clicked.connect(lambda _=False, i=i: self.pick(i))
            row.addWidget(talk)
            col.addLayout(row)
            self.cards.addWidget(card)
        self.cards.addStretch(1)
        self.pages.setCurrentIndex(2)

    def pick(self, index):
        self.on_stage("用意しています…")
        self.core.pick(index)

    def redo(self):
        self.on_stage("作り直しています…")
        self.core.redo()

    def on_trial(self, name):
        self.name = name
        self.trial_title.setText(f"{name}と、お試しで話す")
        self.trial.clear()
        self.trial_input.clear()
        self.set_trial_busy(False)
        self.pages.setCurrentIndex(3)
        self.trial_input.setFocus()

    def set_trial_busy(self, busy):
        self.trial_busy = busy
        for button in (self.send_button, self.back_button, self.confirm_button):
            button.setEnabled(not busy)

    def trial_send(self):
        text = self.trial_input.text().strip()
        if not text or self.trial_busy:
            return
        self.trial_input.clear()
        self.set_trial_busy(True)
        self.core.trial_send(text)

    def on_trial_text(self, text):
        cursor = self.trial.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.trial.ensureCursorVisible()

    def on_trial_failed(self, reason):
        self.on_trial_text(f"（うまく返せなかった：{reason}）")
        self.set_trial_busy(False)

    def confirm(self):
        self.set_trial_busy(True)
        self.core.confirm()


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
