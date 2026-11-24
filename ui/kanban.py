from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QHBoxLayout, QLineEdit, QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from core.i18n import tr
from core.llm import PRIORITIES, STATUSES, new_task
from .styles import STATUS_COLORS
from .widgets import EmptyState, Page, badge, clear_layout, label, priority_badge

STATUS_TITLES = {"To Do": "待办 To Do", "In Progress": "进行中 In Progress", "Done": "已完成 Done"}


class TaskDialog(QDialog):
    def __init__(self, parent=None, default_status: str = "To Do"):
        super().__init__(parent)
        self.setWindowTitle(tr("新增任务"))
        self.setMinimumWidth(420)
        form = QFormLayout(self)
        form.setContentsMargins(24, 22, 24, 18)
        form.setVerticalSpacing(12)

        self.title = QLineEdit()
        self.title.setPlaceholderText(tr("例如：整理 v1.2 需求文档"))
        self.assignee = QLineEdit()
        self.assignee.setPlaceholderText(tr("待定"))
        self.no_deadline = QCheckBox(tr("暂不设定"))
        self.deadline = QDateEdit(QDate.currentDate().addDays(7))
        self.deadline.setCalendarPopup(True)
        self.deadline.setDisplayFormat("yyyy-MM-dd")
        self.no_deadline.toggled.connect(lambda on: self.deadline.setEnabled(not on))
        dl_row = QHBoxLayout()
        dl_row.addWidget(self.deadline, 1)
        dl_row.addWidget(self.no_deadline)
        self.priority = QComboBox()
        for p in PRIORITIES:  # 显示译名，保存时仍取「高 / 中 / 低」
            self.priority.addItem(tr(p), p)
        self.priority.setCurrentIndex(self.priority.findData("中"))
        self.status = QComboBox()
        self.status.addItems(STATUSES)
        self.status.setCurrentText(default_status)

        form.addRow(tr("任务内容"), self.title)
        form.addRow(tr("负责人"), self.assignee)
        form.addRow(tr("截止时间"), dl_row)
        form.addRow(tr("优先级"), self.priority)
        form.addRow(tr("状态"), self.status)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr("添加"))
        buttons.button(QDialogButtonBox.Ok).setObjectName("Primary")
        buttons.button(QDialogButtonBox.Cancel).setText(tr("取消"))
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _accept(self) -> None:
        if not self.title.text().strip():
            self.title.setFocus()
            self.title.setPlaceholderText(tr("任务内容不能为空"))
            return
        self.accept()

    def task(self) -> dict:
        deadline = "" if self.no_deadline.isChecked() else self.deadline.date().toString("yyyy-MM-dd")
        return new_task(
            self.title.text(), self.assignee.text(), deadline,
            self.priority.currentData(), self.status.currentText(),
        )


class TaskCard(QFrame):
    status_changed = Signal(str, str)
    delete_requested = Signal(str)

    def __init__(self, task: dict):
        super().__init__()
        self.setObjectName("TaskCard")
        tid = task["id"]
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(6)
        top.addWidget(priority_badge(task["priority"]))
        top.addStretch()
        delete = QPushButton("✕")
        delete.setObjectName("Danger")
        delete.setToolTip(tr("删除任务"))
        delete.setCursor(Qt.PointingHandCursor)
        delete.clicked.connect(lambda: self.delete_requested.emit(tid))
        top.addWidget(delete)
        lay.addLayout(top)

        title = label(task["task_title"], "Body", wrap=True)
        title.setStyleSheet("font-weight: 600;")
        if task["source_quote"]:
            title.setToolTip(tr("原文：“{quote}”", quote=task["source_quote"]))
        lay.addWidget(title)

        meta = QHBoxLayout()
        meta.setSpacing(6)
        meta.addWidget(badge(f"👤 {tr(task['assignee'])}", "neutral"))
        meta.addWidget(label(f"📅 {tr(task['deadline'])}", "Small"))
        meta.addStretch()
        lay.addLayout(meta)

        box = QComboBox()
        box.setObjectName("StatusBox")
        box.addItems(STATUSES)
        box.setCurrentText(task["status"])
        box.currentTextChanged.connect(lambda s: self.status_changed.emit(tid, s))
        lay.addWidget(box)


class KanbanPage(QWidget):
    tasks_changed = Signal()  # 任务被增删改后通知主窗口保存

    def __init__(self):
        super().__init__()
        self.setObjectName("Workspace")
        self.meeting: dict | None = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.page = Page(max_width=1180)  # 三列看板需要比正文更宽的空间
        outer.addWidget(self.page)
        self.refresh()

    def set_meeting(self, meeting: dict | None) -> None:
        self.meeting = meeting
        self.refresh()

    @property
    def tasks(self) -> list[dict]:
        return self.meeting["result"]["action_items"]

    def refresh(self) -> None:
        body = self.page.body
        clear_layout(body)
        if self.meeting is None:
            body.addWidget(EmptyState(tr("还没有打开任何会议"), tr("先在「会议」中解析一场会议，或从左侧历史记录中选择。")))
            body.addStretch()
            return

        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(label(tr("智能任务看板"), "H2"))
        done = sum(t["status"] == "Done" for t in self.tasks)
        titles.addWidget(label(tr("{title} · 共 {n} 项，已完成 {done} 项",
                                  title=self.meeting["title"], n=len(self.tasks), done=done), "Muted"))
        head.addLayout(titles, 1)
        add = QPushButton(tr("＋ 新增任务"))
        add.setObjectName("Primary")
        add.clicked.connect(lambda: self._add_task("To Do"))
        head.addWidget(add, 0, Qt.AlignTop)
        body.addLayout(head)
        body.addSpacing(6)

        cols = QHBoxLayout()
        cols.setSpacing(14)
        for status in STATUSES:
            cols.addWidget(self._column(status), 1)
        body.addLayout(cols, 1)

    def _column(self, status: str) -> QFrame:
        col = QFrame()
        col.setObjectName("Column")
        col.setMinimumHeight(460)
        lay = QVBoxLayout(col)
        lay.setContentsMargins(12, 14, 12, 12)
        lay.setSpacing(10)

        items = [t for t in self.tasks if t["status"] == status]
        hdr = QHBoxLayout()
        dot = label("●")
        dot.setStyleSheet(f"color: {STATUS_COLORS[status]}; font-size: 12px;")
        hdr.addWidget(dot)
        hdr.addWidget(label(tr(STATUS_TITLES[status]), "H3"))
        hdr.addWidget(label(str(len(items)), "Small"))
        hdr.addStretch()
        lay.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget#qt_scrollarea_viewport { background: transparent; }")
        inner = QWidget()
        inner.setObjectName("ColumnInner")
        inner.setStyleSheet("QWidget#ColumnInner { background: transparent; }")  # 只作用于自身，否则会盖掉卡片里标签的底色
        il = QVBoxLayout(inner)
        il.setContentsMargins(0, 0, 4, 0)
        il.setSpacing(10)
        for t in items:
            c = TaskCard(t)
            c.status_changed.connect(self._set_status)
            c.delete_requested.connect(self._delete)
            il.addWidget(c)
        il.addStretch()
        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)

        add = QPushButton(tr("＋ 添加"))
        add.setObjectName("Ghost")
        add.clicked.connect(lambda: self._add_task(status))
        lay.addWidget(add, 0, Qt.AlignLeft)
        return col

    def _find(self, tid: str) -> dict:
        return next(t for t in self.tasks if t["id"] == tid)

    def _set_status(self, tid: str, status: str) -> None:
        self._find(tid)["status"] = status
        self._changed()

    def _delete(self, tid: str) -> None:
        t = self._find(tid)
        if QMessageBox.question(self, tr("删除任务"), tr("确定删除任务「{title}」吗？", title=t["task_title"])) == QMessageBox.Yes:
            self.tasks.remove(t)
            self._changed()

    def _add_task(self, status: str) -> None:
        dlg = TaskDialog(self, status)
        if dlg.exec() == QDialog.Accepted:
            self.tasks.append(dlg.task())
            self._changed()

    def _changed(self) -> None:
        self.tasks_changed.emit()
        # 状态下拉框的信号仍在执行中，延后重建界面，避免删除正在发信号的控件
        QTimer.singleShot(0, self.refresh)
