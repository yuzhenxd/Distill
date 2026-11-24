import os
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from core.config import Settings, load_settings, save_settings
from core.demo import DEMO_SOURCE, DEMO_TRANSCRIPT
from core.exporter import push_feishu
from core.i18n import set_language, tr
from core.live import LiveError, LiveSession, check_live_ready
from core.llm import LLMError, list_ollama_models, test_connection
from core.pipeline import process_file, process_text
from core.storage import MeetingStore
from core.transcriber import TranscribeError
from core.workers import Worker
from .export_page import ExportPage
from .kanban import KanbanPage
from .live_page import LivePage, fmt_time
from .new_meeting import NewMeetingPage
from .settings_page import SettingsPage
from .sidebar import Sidebar
from .styles import apply_theme

PAGE_NEW, PAGE_LIVE, PAGE_BOARD, PAGE_EXPORT, PAGE_SETTINGS = range(5)


class LiveBridge(QObject):
    """把 LiveSession 在后台线程里的回调转成 Qt 信号，排队送回主线程。"""

    level = Signal(float)
    pending = Signal(int)
    segment = Signal(object)
    error = Signal(str)
    finished = Signal()
    muted = Signal()


class Toast(QLabel):
    """右下角短暂浮现的提示条。"""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, ms: int = 2600) -> None:
        self.setText(text)
        # 短消息单行显示；超过 420px 的长消息（如保存路径）固定宽度后换行
        long = self.fontMetrics().horizontalAdvance(text) + 32 > 420
        self.setWordWrap(long)
        self.setFixedWidth(420) if long else self.setMinimumWidth(0)
        self.setMaximumWidth(420 if long else 16777215)
        self.adjustSize()
        p = self.parentWidget()
        self.move(p.width() - self.width() - 24, p.height() - self.height() - 24)
        self.raise_()
        self.show()
        self._timer.start(ms)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MeetingFlow AI")
        self.resize(1320, 840)
        self.setMinimumSize(980, 640)

        self.settings: Settings = load_settings()
        set_language(self.settings.ui_language)
        apply_theme(QApplication.instance(), self.settings.theme)
        self.store = MeetingStore()
        self.current: dict | None = None
        self.busy = False
        self.live: LiveSession | None = None
        self.live_meeting: dict | None = None   # 正在录制或刚录完的实时会议
        self.live_summarizing = False

        QShortcut(QKeySequence("Ctrl+B"), self, lambda: self.set_sidebar(not self.sidebar.isVisible()))
        self._build_ui()
        self.go(PAGE_NEW)

    def _build_ui(self) -> None:
        """搭建侧边栏和各页面并连接信号；切换界面语言时整体重建一次。"""
        root = QWidget()
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.sidebar = Sidebar()
        row.addWidget(self.sidebar)

        workspace = QWidget()
        workspace.setObjectName("Workspace")
        wl = QVBoxLayout(workspace)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)
        self.expand_btn = QPushButton("»")
        self.expand_btn.setObjectName("IconButton")
        self.expand_btn.setToolTip(tr("展开侧边栏（Ctrl+B）"))
        self.expand_btn.setFixedSize(28, 28)
        self.expand_btn.hide()
        bar = QHBoxLayout()
        bar.setContentsMargins(12, 12, 12, 0)
        bar.addWidget(self.expand_btn)
        bar.addStretch()
        wl.addLayout(bar)

        self.stack = QStackedWidget()
        self.new_page = NewMeetingPage()
        self.live_page = LivePage(self.settings.translate_target)
        self.board_page = KanbanPage()
        self.export_page = ExportPage()
        self.settings_page = SettingsPage(self.settings)
        for p in (self.new_page, self.live_page, self.board_page, self.export_page, self.settings_page):
            self.stack.addWidget(p)
        wl.addWidget(self.stack, 1)
        row.addWidget(workspace, 1)
        self.setCentralWidget(root)
        self.toast = Toast(workspace)

        # ---- 信号连接 ----
        self.sidebar.page_selected.connect(self.go)
        self.sidebar.meeting_selected.connect(self.open_meeting)
        self.sidebar.meeting_delete_requested.connect(self.delete_meeting)
        self.sidebar.collapse_btn.clicked.connect(lambda: self.set_sidebar(False))
        self.expand_btn.clicked.connect(lambda: self.set_sidebar(True))

        self.new_page.file_chosen.connect(self.start_file)
        self.new_page.demo_requested.connect(self.start_demo)
        self.new_page.drop.rejected.connect(self.toast.show_message)
        self.new_page.open_board.connect(lambda: self.go(PAGE_BOARD))
        self.new_page.open_export.connect(lambda: self.go(PAGE_EXPORT))
        self.live_page.start_requested.connect(self.start_live)
        self.live_page.stop_requested.connect(self.stop_live)
        self.live_page.open_meeting.connect(lambda: self.open_meeting(self.live_meeting["id"]))
        self.bridge = LiveBridge()
        self.bridge.level.connect(self.live_page.set_level)
        self.bridge.pending.connect(self.live_page.set_pending)
        self.bridge.segment.connect(self._live_segment)
        self.bridge.error.connect(self.toast.show_message)
        self.bridge.finished.connect(self._live_finished)
        self.bridge.muted.connect(self._live_muted)
        self.board_page.tasks_changed.connect(self.save_current)
        self.export_page.toast.connect(self.toast.show_message)
        self.export_page.webhook_changed.connect(self.save_webhook)
        self.export_page.push_requested.connect(self.push_feishu)
        self.settings_page.save_requested.connect(self.apply_settings)
        self.settings_page.test_requested.connect(self.test_model)
        self.settings_page.ollama_models_requested.connect(self.fetch_ollama_models)
        self.settings_page.theme_changed.connect(self.set_theme)
        self.settings_page.ui_language_changed.connect(self.set_ui_language)

        self.export_page.set_webhook(self.settings.feishu_webhook)
        self.set_current(self.current)

    # ---------- 导航 ----------
    def go(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.sidebar.set_page(index)

    def set_sidebar(self, visible: bool) -> None:
        self.sidebar.animate_visible(visible)
        self.expand_btn.setVisible(not visible)

    def refresh_history(self) -> None:
        self.sidebar.set_history(self.store.list(), self.current and self.current["id"])

    def set_current(self, meeting: dict | None) -> None:
        self.current = meeting
        self.board_page.set_meeting(meeting)
        self.export_page.set_meeting(meeting)
        if meeting:
            self.new_page.show_result(meeting)
        else:
            self.new_page.show_upload()
        self.refresh_history()

    def open_meeting(self, meeting_id: str) -> None:
        meeting = self.store.get(meeting_id)
        if meeting is None:
            self.refresh_history()
            return
        self.set_current(meeting)
        if self.stack.currentIndex() in (PAGE_LIVE, PAGE_SETTINGS):
            self.go(PAGE_NEW)

    def delete_meeting(self, meeting_id: str) -> None:
        meeting = self.store.get(meeting_id)
        if meeting is None:
            return
        if QMessageBox.question(self, tr("删除会议"), tr("确定删除「{title}」及其所有任务吗？此操作无法撤销。", title=meeting["title"])) != QMessageBox.Yes:
            return
        self.store.delete(meeting_id)
        if self.current and self.current["id"] == meeting_id:
            self.set_current(None)
        else:
            self.refresh_history()
        self.toast.show_message(tr("已删除会议"))

    def save_current(self) -> None:
        self.store.update(self.current)
        self.new_page.show_result(self.current)
        self.export_page.set_meeting(self.current)

    # ---------- 会议解析 ----------
    def start_file(self, path: str) -> None:
        self._run_pipeline(process_file, path)

    def start_demo(self) -> None:
        self._run_pipeline(process_text, DEMO_TRANSCRIPT, DEMO_SOURCE)

    def _run_pipeline(self, fn, *args) -> None:
        if self.busy:
            return
        self.busy = True
        self.new_page.set_busy(True)
        self.go(PAGE_NEW)
        w = Worker(fn, *args, self.settings, with_progress=True)
        w.progress.connect(self.new_page.set_progress)
        w.succeeded.connect(self._pipeline_done)
        w.failed.connect(self._pipeline_failed)
        w.start()

    def _pipeline_done(self, out: dict) -> None:
        self.busy = False
        self.new_page.set_busy(False)
        title = out["result"]["meeting_title"] or Path(out["source"]).stem
        meeting = self.store.create(title, out["source"], out["transcript"], out["result"])
        self.set_current(meeting)
        self.toast.show_message(tr("解析完成：识别到 {n} 个行动项", n=len(out["result"]["action_items"])))

    def _pipeline_failed(self, message: str) -> None:
        self.busy = False
        self.new_page.set_busy(False)
        self._warn_with_settings(tr("解析失败"), message)

    # ---------- 实时翻译记录 ----------
    def start_live(self, device, target: str) -> None:
        if self.live or self.live_summarizing:
            return
        if target != self.settings.translate_target:
            self._persist(replace(self.settings, translate_target=target))
        try:
            check_live_ready(self.settings)
        except (TranscribeError, LLMError) as e:
            self._warn_with_settings(tr("无法开始实时翻译"), str(e))
            return
        b = self.bridge
        session = LiveSession(
            self.settings, target, device,
            b.level.emit, b.pending.emit, b.segment.emit, b.error.emit, b.finished.emit, b.muted.emit,
        )
        try:
            session.start()
        except LiveError as e:
            QMessageBox.warning(self, tr("无法开始录音"), str(e))
            return
        self.live = session
        self.live_meeting = None
        self.live_target = target
        self.live_started = datetime.now()
        self.live_page.set_recording()

    def stop_live(self) -> None:
        self.live_page.set_stopping()
        self.live.stop()

    def _live_segment(self, seg: dict) -> None:
        """每识别出一段就写入数据库，录到一半程序退出也不会丢。"""
        self.live_page.add_segment(seg)
        m = self.live_meeting
        if m is None:
            result = {
                "meeting_title": "", "meeting_summary": "", "key_decisions": [], "action_items": [],
                "live_segments": [seg], "translate_target": self.live_target,
            }
            title = tr("实时翻译记录 {time}", time=f"{self.live_started:%m-%d %H:%M}")
            self.live_meeting = self.store.create(
                title, tr("实时录音 · 译为 {target}", target=self.live_target), self._live_transcript([seg]), result
            )
            self.refresh_history()
            return
        m["result"]["live_segments"].append(seg)
        m["transcript"] = self._live_transcript(m["result"]["live_segments"])
        self.store.update(m)

    def _live_muted(self) -> None:
        if not self.live:
            return
        self.stop_live()
        if sys.platform == "darwin":
            hint = (
                "macOS 没有允许本程序使用麦克风，或麦克风被静音。\n\n"
                "请打开「系统设置 → 隐私与安全性 → 麦克风」，打开 MeetingFlow AI 的开关"
                "（从终端运行源码时打开「终端」或启动它的程序），然后重启本程序再录音。"
            )
        elif sys.platform == "win32":
            hint = (
                "Windows 没有允许桌面应用使用麦克风，或麦克风被静音。\n\n"
                "请打开「设置 → 隐私和安全性 → 麦克风」，打开「允许桌面应用访问麦克风」，"
                "并检查声音设置里的输入音量，然后再录音。"
            )
        else:
            hint = "请检查系统的麦克风权限和输入音量，然后再录音。"
        QMessageBox.warning(self, tr("麦克风没有声音"), tr("录音开始 2 秒内收到的全是静音，已停止录音。") + "\n\n" + tr(hint))

    @staticmethod
    def _live_transcript(segments: list[dict]) -> str:
        return "\n".join(f"[{fmt_time(s['start'])}] {s['text']}" for s in segments)

    def _live_finished(self) -> None:
        self.live = None
        m = self.live_meeting
        if m is None:
            self.live_page.set_status(tr("没有识别到语音内容，本次未保存记录。"), done=True)
            return
        self.live_summarizing = True
        self.live_page.set_status(tr("录音已保存到历史会议，正在生成会议纪要和行动项…"))
        w = Worker(process_text, m["transcript"], m["source"], self.settings, with_progress=True)
        w.succeeded.connect(self._live_summary_done)
        w.failed.connect(self._live_summary_failed)
        w.start()

    def _live_summary_done(self, out: dict) -> None:
        self.live_summarizing = False
        m = self.live_meeting
        result = out["result"]
        result["live_segments"] = m["result"]["live_segments"]
        result["translate_target"] = m["result"]["translate_target"]
        m["result"] = result
        if result["meeting_title"]:
            m["title"] = result["meeting_title"]
        self.store.update(m)
        if self.current and self.current["id"] == m["id"]:
            self.set_current(self.store.get(m["id"]))
        else:
            self.refresh_history()
        self.live_page.set_status(
            tr("已保存到历史会议「{title}」，识别到 {n} 个行动项。", title=m["title"], n=len(result["action_items"])),
            done=True, can_view=True,
        )

    def _live_summary_failed(self, message: str) -> None:
        self.live_summarizing = False
        self.live_page.set_status(
            tr("原文与译文已保存到历史会议，但生成纪要失败：{message}", message=message), done=True, can_view=True
        )

    def _warn_with_settings(self, title: str, message: str) -> None:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(title)
        box.setText(message)
        settings_btn = box.addButton(tr("前往设置"), QMessageBox.ActionRole)
        box.addButton(tr("好的"), QMessageBox.AcceptRole)
        box.exec()
        if box.clickedButton() is settings_btn:
            self.go(PAGE_SETTINGS)

    # ---------- 设置 ----------
    def _persist(self, settings: Settings) -> None:
        self.settings = settings
        self.settings_page.settings = settings
        save_settings(settings)

    def apply_settings(self, settings: Settings) -> None:
        self._persist(settings)
        self.toast.show_message(tr("设置已保存"))

    def set_theme(self, theme: str) -> None:
        apply_theme(QApplication.instance(), theme)
        self._persist(replace(self.settings, theme=theme))

    def set_ui_language(self, lang: str) -> None:
        if self.live or self.live_summarizing or self.busy:
            self.toast.show_message(tr("正在录音或处理中，请结束后再切换语言"))
            self.settings_page.revert_ui_language(self.settings.ui_language)
            return
        set_language(lang)
        self._persist(replace(self.settings, ui_language=lang))
        # 信号来自设置页的单选框，等它的处理结束后再销毁、重建整个界面
        QTimer.singleShot(0, self._rebuild_ui)

    def _rebuild_ui(self) -> None:
        self._build_ui()
        self.go(PAGE_SETTINGS)

    def save_webhook(self, url: str) -> None:
        self._persist(replace(self.settings, feishu_webhook=url))

    def test_model(self, settings: Settings) -> None:
        self.settings_page.set_test_busy()
        w = Worker(test_connection, settings)
        w.succeeded.connect(lambda msg: self.settings_page.set_test_result(True, msg))
        w.failed.connect(lambda msg: self.settings_page.set_test_result(False, msg))
        w.start()

    def fetch_ollama_models(self, base_url: str) -> None:
        w = Worker(list_ollama_models, base_url)
        w.succeeded.connect(self._ollama_models_loaded)
        w.failed.connect(self.toast.show_message)
        w.start()

    def _ollama_models_loaded(self, models: list) -> None:
        if models:
            self.settings_page.set_ollama_models(models)
            self.toast.show_message(tr("找到 {n} 个本地模型", n=len(models)))
        else:
            self.toast.show_message(tr("Ollama 中还没有模型，请先执行 ollama pull"))

    # ---------- 飞书 ----------
    def push_feishu(self, webhook: str, payload: dict) -> None:
        w = Worker(push_feishu, webhook, payload)
        w.succeeded.connect(self.toast.show_message)
        w.failed.connect(lambda msg: QMessageBox.warning(self, tr("推送失败"), msg))
        w.finished.connect(self.export_page.push_finished)
        w.start()

    def closeEvent(self, event) -> None:
        if self.live or self.live_summarizing:
            question = (tr("实时录音"), tr("正在录音或生成纪要。已识别的内容都已保存，但尚未处理的片段和会议纪要会丢失，确定要退出吗？"))
        elif self.busy:
            question = (tr("正在解析"), tr("会议仍在解析中，确定要退出吗？"))
        else:
            question = None
        if question and QMessageBox.question(self, *question) != QMessageBox.Yes:
            event.ignore()
            return
        self.store.close()
        event.accept()
        if Worker._running or self.live:
            # 后台线程卡在网络请求、转写或录音中无法安全中断，直接结束进程，避免 Qt 销毁运行中的线程时崩溃
            os._exit(0)
