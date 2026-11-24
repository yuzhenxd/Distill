"""MeetingFlow AI - Pydantic 数据模型与字段校验。"""
from __future__ import annotations

import uuid
from typing import List

from pydantic import BaseModel, Field, field_validator

PRIORITIES = ["High", "Medium", "Low"]
STATUSES = ["To Do", "In Progress", "Done"]

# 模型输出里常见的同义写法 -> 标准值
_PRIORITY_ALIASES = {
    "high": "High", "高": "High", "紧急": "High", "p0": "High", "p1": "High",
    "medium": "Medium", "中": "Medium", "normal": "Medium", "p2": "Medium",
    "low": "Low", "低": "Low", "p3": "Low",
}
_STATUS_ALIASES = {
    "to do": "To Do", "todo": "To Do", "待办": "To Do", "未开始": "To Do",
    "in progress": "In Progress", "inprogress": "In Progress",
    "doing": "In Progress", "进行中": "In Progress",
    "done": "Done", "已完成": "Done", "完成": "Done",
}


def _new_id() -> str:
    return uuid.uuid4().hex[:8]


class TaskItem(BaseModel):
    """看板上的一张任务卡片。"""

    id: str = Field(default_factory=_new_id)
    title: str = Field(..., description="任务标题，一句话说清要做什么")
    assignee: str = Field(default="未指定", description="负责人姓名")
    deadline: str = Field(default="待定", description="截止时间，如 2026-12-01 或 '下周三前'")
    priority: str = Field(default="Medium", description="High / Medium / Low")
    status: str = Field(default="To Do", description="To Do / In Progress / Done")
    source_quote: str = Field(default="", description="支撑该任务的会议原文引用，用于防幻觉核验")

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("任务标题不能为空")
        return v

    @field_validator("assignee", "deadline", mode="before")
    @classmethod
    def fill_defaults(cls, v, info):
        v = str(v or "").strip()
        if not v or v.lower() in {"none", "null", "n/a", "unknown"}:
            return "未指定" if info.field_name == "assignee" else "待定"
        return v

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v) -> str:
        key = str(v or "").strip().lower()
        if key in _PRIORITY_ALIASES:
            return _PRIORITY_ALIASES[key]
        return "Medium"

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v) -> str:
        key = str(v or "").strip().lower()
        if key in _STATUS_ALIASES:
            return _STATUS_ALIASES[key]
        return "To Do"

    @field_validator("source_quote", mode="before")
    @classmethod
    def quote_to_str(cls, v) -> str:
        return str(v or "").strip()


class MeetingAnalysis(BaseModel):
    """一次会议文本分析的完整结果。"""

    summary: str = Field(..., description="会议核心摘要，3-5 句话")
    decisions: List[str] = Field(default_factory=list, description="关键决策结论列表")
    tasks: List[TaskItem] = Field(default_factory=list, description="提炼出的待办任务")

    @field_validator("summary", mode="before")
    @classmethod
    def summary_to_str(cls, v) -> str:
        return str(v or "").strip() or "（模型未返回摘要）"

    @field_validator("decisions", mode="before")
    @classmethod
    def decisions_to_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return [str(item).strip() for item in v if str(item).strip()]
