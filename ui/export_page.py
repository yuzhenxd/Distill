from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLineEdit, QPlainTextEdit, QPushButton,
    QVBoxLayout, QWidget,
)

from core.exporter import to_feishu_post, to_json, to_markdown
from core.i18n import tr
from .widgets import EmptyState, Page, card, clear_layout, label

FORMATS = [
    ("json", "JSON", ".json", "JSON 文件 (*.json)"),
    ("md", "Markdown", ".md", "Markdown 文件 (*.md)"),
    ("feishu", "飞书消息", "", ""),  # 只推送到群，不另存为文件
]


class ExportPage(QWidget):
    push_requested = Signal(str, dict)  # webhook, payload
    webhook_changed = Signal(str)
    toast = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("Workspace")
        self.meeting: dict | None = None
        self.fmt = "json"
        self.webhook = ""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.page = Page()
        outer.addWidget(self.page)
        self.refresh()

    def set_meeting(self, meeting: dict | None) -> None:
        self.meeting = meeting
        self.refresh()

    def set_webhook(self, url: str) -> None:
        self.webhook = url
        self.refresh()

    def _content(self) -> str:
        if self.fmt == "md":
            return to_markdown(self.meeting)
        return to_json(self.meeting)

    def refresh(self) -> None:
        body = self.page.body
        clear_layout(body)
        if self.meeting is None:
            body.addWidget(EmptyState(tr("还没有可导出的会议"), tr("解析一场会议后，可在这里导出 JSON / Markdown 或推送到飞书。")))
            body.addStretch()
            return

        self.page.header(tr("导出与同步"), tr("当前会议：{title}", title=self.meeting["title"]))

        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        for key, name, _, _ in FORMATS:
            b = QPushButton(tr(name))
            b.setObjectName("Pill")
            b.setProperty("selected", key == self.fmt)
            b.clicked.connect(lambda _=False, k=key: self._switch(k))
            tabs.addWidget(b)
        tabs.addStretch()
        body.addLayout(tabs)

        if self.fmt == "feishu":  # 飞书只推送到群，不预览、不另存
            frame, lay = card()
            lay.addWidget(label(tr("推送到飞书群"), "H3"))
            lay.addWidget(label(tr("在飞书群设置 → 群机器人 → 添加「自定义机器人」，复制 Webhook 地址粘贴到下方。"), "Muted", wrap=True))
            row = QHBoxLayout()
            self.webhook_edit = QLineEdit(self.webhook)
            self.webhook_edit.setPlaceholderText("https://open.feishu.cn/open-apis/bot/v2/hook/…")
            self.webhook_edit.editingFinished.connect(self._webhook_edited)
            self.push_btn = QPushButton(tr("推送"))
            self.push_btn.setObjectName("Primary")
            self.push_btn.clicked.connect(self._push)
            row.addWidget(self.webhook_edit, 1)
            row.addWidget(self.push_btn)
            lay.addLayout(row)
            body.addWidget(frame)
            body.addStretch()
            return

        frame, lay = card()
        preview = QPlainTextEdit(self._content())
        preview.setReadOnly(True)
        preview.setMinimumHeight(360)
        mono = QFont("Menlo")
        mono.setStyleHint(QFont.Monospace)
        mono.setPointSize(12)
        preview.setFont(mono)
        preview.setStyleSheet("border: none; padding: 0;")
        lay.addWidget(preview)
        body.addWidget(frame)

        actions = QHBoxLayout()
        copy = QPushButton(tr("复制到剪贴板"))
        copy.clicked.connect(self._copy)
        save = QPushButton(tr("保存为文件…"))
        save.setObjectName("Primary")
        save.clicked.connect(self._save)
        actions.addStretch()
        actions.addWidget(copy)
        actions.addWidget(save)
        body.addLayout(actions)
        body.addStretch()

    def _switch(self, key: str) -> None:
        self.fmt = key
        self.refresh()

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self._content())
        self.toast.emit(tr("已复制到剪贴板"))

    def _save(self) -> None:
        _, name, ext, flt = next(f for f in FORMATS if f[0] == self.fmt)
        safe = "".join(c for c in self.meeting["title"] if c not in '\\/:*?"<>|').strip() or "meeting"
        default = str(Path.home() / f"{safe}{ext}")
        path, _ = QFileDialog.getSaveFileName(self, tr("导出 {name}", name=tr(name)), default, tr(flt))
        if path:
            Path(path).write_text(self._content(), "utf-8")
            self.toast.emit(tr("已保存：{path}", path=path))

    def _webhook_edited(self) -> None:
        url = self.webhook_edit.text().strip()
        if url != self.webhook:
            self.webhook = url
            self.webhook_changed.emit(url)

    def _push(self) -> None:
        self._webhook_edited()
        if not self.webhook.startswith("https://"):
            self.toast.emit(tr("请填写以 https:// 开头的飞书 Webhook 地址"))
            return
        self.push_btn.setEnabled(False)
        self.push_btn.setText(tr("推送中…"))
        self.push_requested.emit(self.webhook, to_feishu_post(self.meeting))

    def push_finished(self) -> None:
        if self.fmt == "feishu" and self.meeting is not None:
            self.push_btn.setEnabled(True)
            self.push_btn.setText(tr("推送"))
