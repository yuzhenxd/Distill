from PySide6.QtCore import QElapsedTimer, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from core.i18n import tr
from core.live import TARGET_LANGUAGES, level_percent, list_input_devices
from .widgets import EmptyState, Page, card, clear_layout, label


def fmt_time(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def segment_widget(seg: dict) -> QWidget:
    w = QFrame()
    w.setObjectName("Segment")
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 10, 0, 10)
    lay.setSpacing(14)
    ts = label(fmt_time(seg["start"]), "Small")
    ts.setFixedWidth(40)
    lay.addWidget(ts, 0, Qt.AlignTop)
    col = QVBoxLayout()
    col.setSpacing(4)
    col.addWidget(label(seg["text"], "Body", wrap=True, selectable=True))
    if seg["translation"]:
        col.addWidget(label(seg["translation"], "Translation", wrap=True, selectable=True))
    lay.addLayout(col, 1)
    return w


class LivePage(QWidget):
    start_requested = Signal(object, str)   # 设备序号（None 为系统默认）, 目标语言
    stop_requested = Signal()
    open_meeting = Signal()

    def __init__(self, target: str):
        super().__init__()
        self.setObjectName("Workspace")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.page = Page()
        outer.addWidget(self.page)
        body = self.page.body
        self.page.header(tr("实时翻译记录"), tr("边说边转写、边翻译。记录会自动保存到历史会议，结束后自动生成会议纪要和行动项。"))

        frame, lay = card()
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(label(tr("麦克风"), "Muted"))
        self.device = QComboBox()
        self.device.setMinimumWidth(220)
        row.addWidget(self.device, 1)
        refresh = QPushButton("↻")
        refresh.setToolTip(tr("重新检测麦克风"))
        refresh.clicked.connect(self.load_devices)
        row.addWidget(refresh)
        row.addSpacing(10)
        row.addWidget(label(tr("翻译为"), "Muted"))
        self.target = QComboBox()
        self.target.addItems(TARGET_LANGUAGES)
        self.target.setCurrentText(target if target in TARGET_LANGUAGES else "English")
        row.addWidget(self.target)
        row.addSpacing(10)
        self.toggle_btn = QPushButton(tr("● 开始录音"))
        self.toggle_btn.setObjectName("Primary")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle)
        row.addWidget(self.toggle_btn)
        lay.addLayout(row)

        status = QHBoxLayout()
        status.setSpacing(12)
        self.level = QProgressBar()
        self.level.setTextVisible(False)
        self.level.setRange(0, 100)
        self.level.setFixedWidth(160)
        status.addWidget(self.level)
        self.status = label(tr("准备就绪"), "Small")
        status.addWidget(self.status, 1)
        self.view_btn = QPushButton(tr("查看会议纪要 →"))
        self.view_btn.setObjectName("Ghost")
        self.view_btn.clicked.connect(self.open_meeting.emit)
        self.view_btn.hide()
        status.addWidget(self.view_btn)
        lay.addLayout(status)
        body.addWidget(frame)

        frame, self.transcript = card()
        self.transcript.setSpacing(0)
        body.addWidget(frame)
        body.addStretch()

        self.recording = False
        self.stopping = False
        self.pending = 0
        self.clock = QElapsedTimer()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_status)
        self.load_devices()
        self._show_empty()

    # ---------- 控件状态 ----------
    def load_devices(self) -> None:
        devices, default = list_input_devices()
        self.device.clear()
        for index, name in devices:
            self.device.addItem(name, index)
        if default is not None:
            self.device.setCurrentIndex(self.device.findData(default))
        if not devices:
            self.device.addItem(tr("未检测到麦克风"), None)
        self.toggle_btn.setEnabled(bool(devices) and not self.stopping)

    def _toggle(self) -> None:
        if self.recording:
            self.stop_requested.emit()
        else:
            self.start_requested.emit(self.device.currentData(), self.target.currentText())

    def _show_empty(self) -> None:
        clear_layout(self.transcript)
        self.transcript.addWidget(EmptyState("🌐", tr("还没有开始"), tr("点击「开始录音」，说话内容会逐段显示原文与译文。")))

    def set_recording(self) -> None:
        self.recording = True
        self.pending = 0
        clear_layout(self.transcript)
        self.view_btn.hide()
        self.device.setEnabled(False)
        self.target.setEnabled(False)
        self.toggle_btn.setText(tr("■ 结束并保存"))
        self.clock.start()
        self.timer.start(500)
        self._refresh_status()

    def set_stopping(self) -> None:
        self.recording = False
        self.stopping = True
        self.timer.stop()
        self.level.setValue(0)
        self.toggle_btn.setEnabled(False)
        self.toggle_btn.setText(tr("● 开始录音"))
        self._refresh_status()

    def set_status(self, text: str, done: bool = False, can_view: bool = False) -> None:
        """处理结束（done）后恢复可以开始新一场录音。"""
        if done:
            self.stopping = False
            self.device.setEnabled(True)
            self.target.setEnabled(True)
            self.toggle_btn.setEnabled(self.device.currentData() is not None)
            if not self.transcript.count():
                self._show_empty()
        self.view_btn.setVisible(can_view)
        self.status.setText(text)

    def _refresh_status(self) -> None:
        if self.recording:
            text = tr("● 录音中 {time}", time=fmt_time(self.clock.elapsed() / 1000))
        else:
            text = tr("录音已结束，正在处理剩余片段")
        if self.pending:
            text += tr(" · {n} 段识别翻译中…", n=self.pending)
        self.status.setText(text)

    # ---------- 会话回调 ----------
    def set_level(self, rms: float) -> None:
        if self.recording:
            self.level.setValue(level_percent(rms))

    def set_pending(self, n: int) -> None:
        self.pending = n
        if self.recording or self.stopping:
            self._refresh_status()

    def add_segment(self, seg: dict) -> None:
        bar = self.page.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 40
        if self.transcript.count():
            line = QFrame()
            line.setFixedHeight(1)
            line.setObjectName("Divider")
            self.transcript.addWidget(line)
        self.transcript.addWidget(segment_widget(seg))
        if at_bottom:  # 用户往上翻看时不打断
            QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))
