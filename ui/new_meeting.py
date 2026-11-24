from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QProgressBar, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from core.transcriber import AUDIO_EXTS, TEXT_EXTS
from .styles import STATUS_COLORS
from .widgets import Page, card, clear_layout, label, priority_badge

SUPPORTED = AUDIO_EXTS | TEXT_EXTS
FILE_FILTER = "会议录音或文本 (*.mp3 *.wav *.m4a *.txt *.md)"


class DropZone(QFrame):
    file_dropped = Signal(str)
    rejected = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(220)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addStretch()
        for text, name, style in (
            ("⬆", "", "font-size: 34px; color: #D97757;"),
            ("拖拽会议录音或文本到这里", "H3", ""),
            ("或点击选择文件 · 支持 .mp3 / .wav / .m4a / .txt / .md", "Muted", ""),
        ):
            w = label(text, name)
            w.setAlignment(Qt.AlignCenter)
            if style:
                w.setStyleSheet(style)
            layout.addWidget(w)
        layout.addStretch()

    def _set_hover(self, on: bool) -> None:
        self.setProperty("hover", on)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            path, _ = QFileDialog.getOpenFileName(self, "选择会议文件", "", FILE_FILTER)
            if path:
                self.file_dropped.emit(path)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_hover(True)

    def dragLeaveEvent(self, event) -> None:
        self._set_hover(False)

    def dropEvent(self, event) -> None:
        self._set_hover(False)
        urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
        if not urls:
            return
        path = urls[0].toLocalFile()
        if Path(path).suffix.lower() in SUPPORTED:
            self.file_dropped.emit(path)
        else:
            self.rejected.emit(f"不支持的文件格式：{Path(path).name}")


class NewMeetingPage(QStackedWidget):
    file_chosen = Signal(str)
    demo_requested = Signal()
    open_board = Signal()
    open_export = Signal()

    def __init__(self):
        super().__init__()
        self.addWidget(self._build_upload())
        self.result_page = Page()
        self.addWidget(self.result_page)

    # ---------- 上传页 ----------
    def _build_upload(self) -> QWidget:
        page = Page()
        body = page.body
        body.addStretch(2)
        title = label("今天要整理哪场会议？", "H1")
        title.setAlignment(Qt.AlignCenter)
        sub = label("上传录音或会议文本，MeetingFlow 会为你提炼摘要、关键决策，并把行动项排进任务看板。", "Muted", wrap=True)
        sub.setAlignment(Qt.AlignCenter)
        body.addWidget(title)
        body.addWidget(sub)
        body.addSpacing(18)

        self.drop = DropZone()
        self.drop.file_dropped.connect(self.file_chosen.emit)
        body.addWidget(self.drop)

        row = QHBoxLayout()
        row.addStretch()
        self.demo_btn = QPushButton("⚡ 加载内置演示会议")
        self.demo_btn.setObjectName("Pill")
        self.demo_btn.setCursor(Qt.PointingHandCursor)
        self.demo_btn.clicked.connect(self.demo_requested.emit)
        row.addWidget(self.demo_btn)
        row.addStretch()
        body.addSpacing(4)
        body.addLayout(row)

        # 进度状态
        self.progress_box = QFrame()
        self.progress_box.setObjectName("Card")
        pl = QVBoxLayout(self.progress_box)
        pl.setContentsMargins(20, 16, 20, 16)
        pl.setSpacing(10)
        self.progress_label = label("", "Body", wrap=True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        pl.addWidget(self.progress_label)
        pl.addWidget(self.progress_bar)
        self.progress_box.hide()
        body.addSpacing(8)
        body.addWidget(self.progress_box)
        body.addStretch(3)
        return page

    def set_busy(self, busy: bool) -> None:
        self.drop.setEnabled(not busy)
        self.demo_btn.setEnabled(not busy)
        self.progress_box.setVisible(busy)
        if busy:
            self.setCurrentIndex(0)
            self.set_progress(0, "准备中…")

    def set_progress(self, pct: int, message: str) -> None:
        self.progress_label.setText(message)
        if pct < 0:
            self.progress_bar.setRange(0, 0)  # 未知进度：忙碌动画
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(pct)

    def show_upload(self) -> None:
        self.setCurrentIndex(0)

    # ---------- 结果页 ----------
    def show_result(self, meeting: dict) -> None:
        r = meeting["result"]
        body = self.result_page.body
        clear_layout(body)

        top = QHBoxLayout()
        head = QVBoxLayout()
        head.setSpacing(4)
        head.addWidget(label(meeting["title"], "H2", wrap=True))
        head.addWidget(label(f"{meeting['created_at']} · {meeting['source']}", "Small"))
        top.addLayout(head, 1)
        new_btn = QPushButton("＋ 新建解析")
        new_btn.clicked.connect(self.show_upload)
        top.addWidget(new_btn, 0, Qt.AlignTop)
        body.addLayout(top)
        body.addSpacing(4)

        frame, lay = card()
        lay.addWidget(label("会议摘要", "H3"))
        lay.addWidget(label(r["meeting_summary"] or "（模型未给出摘要）", "Body", wrap=True, selectable=True))
        body.addWidget(frame)

        frame, lay = card()
        lay.addWidget(label("关键决策", "H3"))
        for i, d in enumerate(r["key_decisions"], 1):
            lay.addWidget(label(f"{i}.  {d}", "Body", wrap=True, selectable=True))
        if not r["key_decisions"]:
            lay.addWidget(label("（无）", "Muted"))
        body.addWidget(frame)

        frame, lay = card()
        hdr = QHBoxLayout()
        hdr.addWidget(label(f"行动项 · {len(r['action_items'])}", "H3"))
        hdr.addStretch()
        board_btn = QPushButton("在任务看板中管理 →")
        board_btn.setObjectName("Primary")
        board_btn.clicked.connect(self.open_board.emit)
        hdr.addWidget(board_btn)
        lay.addLayout(hdr)
        for t in r["action_items"]:
            lay.addWidget(self._task_row(t))
        if not r["action_items"]:
            lay.addWidget(label("会议中没有识别到明确的行动项。", "Muted"))
        body.addWidget(frame)

        export_btn = QPushButton("📤 导出与同步")
        export_btn.setObjectName("Ghost")
        export_btn.clicked.connect(self.open_export.emit)
        body.addWidget(export_btn, 0, Qt.AlignLeft)
        body.addStretch()
        self.setCurrentIndex(1)
        self.result_page.verticalScrollBar().setValue(0)

    def _task_row(self, t: dict) -> QWidget:
        w = QFrame()
        w.setObjectName("TaskRow")
        w.setStyleSheet("QFrame#TaskRow { border-top: 1px solid #EFEDE6; }")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 10, 0, 4)
        lay.setSpacing(6)
        title = label(t["task_title"], "Body", wrap=True)
        title.setStyleSheet("font-weight: 600;")
        lay.addWidget(title)
        meta = QHBoxLayout()
        meta.setSpacing(8)
        meta.addWidget(priority_badge(t["priority"]))
        meta.addWidget(label(f"👤 {t['assignee']}    📅 {t['deadline']}", "Small"))
        st = label(f"● {t['status']}", "Small")
        st.setStyleSheet(f"color: {STATUS_COLORS[t['status']]};")
        meta.addWidget(st)
        meta.addStretch()
        lay.addLayout(meta)
        if t["source_quote"]:
            q = label(f"“{t['source_quote']}”", "Small", wrap=True, selectable=True)
            q.setStyleSheet("font-style: italic;")
            lay.addWidget(q)
        return w
