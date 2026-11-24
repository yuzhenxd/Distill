import os
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QStackedWidget,
    QVBoxLayout, QWidget,
)

from core.config import Settings, load_settings, save_settings
from core.demo import DEMO_SOURCE, DEMO_TRANSCRIPT
from core.exporter import push_feishu
from core.llm import list_ollama_models, test_connection
from core.pipeline import process_file, process_text
from core.storage import MeetingStore
from core.workers import Worker
from .export_page import ExportPage
from .kanban import KanbanPage
from .new_meeting import NewMeetingPage
from .settings_page import SettingsPage
from .sidebar import Sidebar

PAGE_NEW, PAGE_BOARD, PAGE_EXPORT, PAGE_SETTINGS = range(4)


class Toast(QLabel):
    """右下角短暂浮现的提示条。"""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setStyleSheet(
            "background: #1A1915; color: #FAF9F5; border-radius: 10px; padding: 10px 16px; font-size: 13px;"
        )
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
        self.store = MeetingStore()
        self.current: dict | None = None
        self.busy = False

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
        self.expand_btn.setToolTip("展开侧边栏（Ctrl+B）")
        self.expand_btn.setFixedSize(28, 28)
        self.expand_btn.hide()
        bar = QHBoxLayout()
        bar.setContentsMargins(12, 12, 12, 0)
        bar.addWidget(self.expand_btn)
        bar.addStretch()
        wl.addLayout(bar)

        self.stack = QStackedWidget()
        self.new_page = NewMeetingPage()
        self.board_page = KanbanPage()
        self.export_page = ExportPage()
        self.settings_page = SettingsPage(self.settings)
        for p in (self.new_page, self.board_page, self.export_page, self.settings_page):
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
        QShortcut(QKeySequence("Ctrl+B"), self, lambda: self.set_sidebar(not self.sidebar.isVisible()))

        self.new_page.file_chosen.connect(self.start_file)
        self.new_page.demo_requested.connect(self.start_demo)
        self.new_page.drop.rejected.connect(self.toast.show_message)
        self.new_page.open_board.connect(lambda: self.go(PAGE_BOARD))
        self.new_page.open_export.connect(lambda: self.go(PAGE_EXPORT))
        self.board_page.tasks_changed.connect(self.save_current)
        self.export_page.toast.connect(self.toast.show_message)
        self.export_page.webhook_changed.connect(self.save_webhook)
        self.export_page.push_requested.connect(self.push_feishu)
        self.settings_page.save_requested.connect(self.apply_settings)
        self.settings_page.test_requested.connect(self.test_model)
        self.settings_page.ollama_models_requested.connect(self.fetch_ollama_models)

        self.export_page.set_webhook(self.settings.feishu_webhook)
        self.refresh_history()
        self.go(PAGE_NEW)

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
        if self.stack.currentIndex() == PAGE_SETTINGS:
            self.go(PAGE_NEW)

    def delete_meeting(self, meeting_id: str) -> None:
        meeting = self.store.get(meeting_id)
        if meeting is None:
            return
        if QMessageBox.question(self, "删除会议", f"确定删除「{meeting['title']}」及其所有任务吗？此操作无法撤销。") != QMessageBox.Yes:
            return
        self.store.delete(meeting_id)
        if self.current and self.current["id"] == meeting_id:
            self.set_current(None)
        else:
            self.refresh_history()
        self.toast.show_message("已删除会议")

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
        self.toast.show_message(f"解析完成：识别到 {len(out['result']['action_items'])} 个行动项")

    def _pipeline_failed(self, message: str) -> None:
        self.busy = False
        self.new_page.set_busy(False)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("解析失败")
        box.setText(message)
        settings_btn = box.addButton("前往设置", QMessageBox.ActionRole)
        box.addButton("好的", QMessageBox.AcceptRole)
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
        self.toast.show_message("设置已保存")

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
            self.toast.show_message(f"找到 {len(models)} 个本地模型")
        else:
            self.toast.show_message("Ollama 中还没有模型，请先执行 ollama pull")

    # ---------- 飞书 ----------
    def push_feishu(self, webhook: str, payload: dict) -> None:
        w = Worker(push_feishu, webhook, payload)
        w.succeeded.connect(self.toast.show_message)
        w.failed.connect(lambda msg: QMessageBox.warning(self, "推送失败", msg))
        w.finished.connect(self.export_page.push_finished)
        w.start()

    def closeEvent(self, event) -> None:
        if self.busy and QMessageBox.question(
            self, "正在解析", "会议仍在解析中，确定要退出吗？"
        ) != QMessageBox.Yes:
            event.ignore()
            return
        self.store.close()
        event.accept()
        if Worker._running:
            # 后台线程卡在网络请求或转写中无法安全中断，直接结束进程，避免 Qt 销毁运行中的线程时崩溃
            os._exit(0)
