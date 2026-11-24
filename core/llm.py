import json
import os
import re
import urllib.request
import uuid
from datetime import date

import openai
from openai import OpenAI

from .config import Settings

PRIORITIES = ("高", "中", "低")
STATUSES = ("To Do", "In Progress", "Done")

_PRIORITY_MAP = {"high": "高", "medium": "中", "mid": "中", "low": "低",
                 "p0": "高", "p1": "中", "p2": "低", "紧急": "高", "一般": "中"}
_STATUS_MAP = {"todo": "To Do", "to do": "To Do", "待办": "To Do", "未开始": "To Do",
               "in progress": "In Progress", "doing": "In Progress", "进行中": "In Progress",
               "done": "Done", "completed": "Done", "已完成": "Done"}

SYSTEM_PROMPT = """你是一名专业的会议纪要助理。阅读用户提供的会议记录，只输出一个 JSON 对象，结构如下：
{
  "meeting_title": "不超过 20 字的会议标题",
  "meeting_summary": "150~400 字的会议摘要，概括背景、讨论要点与结论",
  "key_decisions": ["关键决策 1", "关键决策 2"],
  "action_items": [
    {
      "task_title": "动词开头、具体可执行的任务描述",
      "assignee": "负责人姓名，原文未提及填“待定”",
      "deadline": "YYYY-MM-DD；原文没有时间填“未定”",
      "priority": "高 | 中 | 低",
      "status": "To Do | In Progress | Done",
      "source_quote": "会议原文中支撑该任务的原句"
    }
  ]
}
规则：
1. 今天是 {today}。原文中“明天”“下周五”等相对时间请换算成具体日期。
2. source_quote 必须逐字摘自原文，不要改写。
3. status 依据原文判断：已经完成的为 Done，正在做的为 In Progress，其余为 To Do。
4. 不要编造原文没有的任务或决策。"""


class LLMError(Exception):
    pass


def make_client(s: Settings) -> tuple[OpenAI, str]:
    if s.provider == "ollama":
        # Ollama 的 OpenAI 兼容接口不校验 Key，但 SDK 要求非空
        return OpenAI(base_url=s.ollama_base_url, api_key="ollama", timeout=300), s.ollama_model
    key = s.deepseek_api_key or os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        raise LLMError("尚未配置 DeepSeek API Key，请前往「模型与 API 设置」填写。")
    return OpenAI(base_url=s.deepseek_base_url, api_key=key, timeout=180), s.deepseek_model


def _chat(s: Settings, messages: list[dict], **kwargs) -> str:
    client, model = make_client(s)
    try:
        resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
    except openai.AuthenticationError:
        raise LLMError("API Key 无效或已过期，请在设置页检查。") from None
    except openai.APITimeoutError:  # 是 APIConnectionError 的子类，必须先捕获
        raise LLMError("模型响应超时，请稍后重试。") from None
    except openai.APIConnectionError:
        where = "本地 Ollama（请确认已运行 ollama serve）" if s.provider == "ollama" else "DeepSeek 服务"
        raise LLMError(f"无法连接到{where}，请检查网络或服务地址。") from None
    except openai.NotFoundError:
        raise LLMError(f"模型「{model}」不存在，请在设置页确认模型名称。") from None
    except openai.APIStatusError as e:
        raise LLMError(f"模型服务返回错误（HTTP {e.status_code}）：{e.message}") from None
    return resp.choices[0].message.content or ""


def analyze_transcript(text: str, s: Settings) -> dict:
    content = _chat(
        s,
        [
            {"role": "system", "content": SYSTEM_PROMPT.replace("{today}", date.today().isoformat())},
            {"role": "user", "content": f"以下是会议记录：\n\n{text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return normalize_result(_parse_json(content))


def test_connection(s: Settings) -> str:
    _chat(s, [{"role": "user", "content": "ping"}], max_tokens=5)
    model = s.ollama_model if s.provider == "ollama" else s.deepseek_model
    return f"连接成功：{model}"


def list_ollama_models(base_url: str) -> list[str]:
    root = base_url.rstrip("/").removesuffix("/v1")
    try:
        with urllib.request.urlopen(f"{root}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except OSError:
        raise LLMError("无法连接本地 Ollama，请先运行 ollama serve。") from None
    return [m["name"] for m in data.get("models", [])]


def _parse_json(content: str) -> dict:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.S)  # 本地小模型偶尔会在 JSON 外包一层说明文字
        try:
            data = json.loads(match.group(0)) if match else None
        except json.JSONDecodeError:
            data = None
    if not isinstance(data, dict):
        raise LLMError("模型返回的内容不是合法 JSON，请重试或更换模型。")
    return data


def norm_priority(value) -> str:
    v = str(value or "").strip()
    return v if v in PRIORITIES else _PRIORITY_MAP.get(v.lower(), "中")


def norm_status(value) -> str:
    v = str(value or "").strip()
    return v if v in STATUSES else _STATUS_MAP.get(v.lower(), "To Do")


def new_task(task_title: str, assignee: str = "", deadline: str = "", priority: str = "中",
             status: str = "To Do", source_quote: str = "") -> dict:
    return {
        "id": uuid.uuid4().hex[:8],
        "task_title": task_title.strip(),
        "assignee": assignee.strip() or "待定",
        "deadline": deadline.strip() or "未定",
        "priority": norm_priority(priority),
        "status": norm_status(status),
        "source_quote": source_quote.strip(),
    }


def normalize_result(data: dict) -> dict:
    items = []
    for raw in data.get("action_items") or []:
        if not isinstance(raw, dict) or not str(raw.get("task_title") or "").strip():
            continue
        items.append(new_task(
            str(raw.get("task_title")),
            str(raw.get("assignee") or ""),
            str(raw.get("deadline") or ""),
            raw.get("priority"),
            raw.get("status"),
            str(raw.get("source_quote") or ""),
        ))
    decisions = [str(d).strip() for d in data.get("key_decisions") or [] if str(d).strip()]
    return {
        "meeting_title": str(data.get("meeting_title") or "").strip(),
        "meeting_summary": str(data.get("meeting_summary") or "").strip(),
        "key_decisions": decisions,
        "action_items": items,
    }
