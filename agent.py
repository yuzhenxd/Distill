"""MeetingFlow AI - LLM 调用、异常处理与音频转写。

DeepSeek 云端和本地 Ollama 共用同一套 openai SDK 调用逻辑，
只切换 base_url / api_key / model。
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from dataclasses import dataclass
from typing import Optional

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    RateLimitError,
)
from pydantic import ValidationError

from schemas import MeetingAnalysis

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

MAX_RETRIES = 3
REQUEST_TIMEOUT = 60  # 秒


class MeetingFlowError(Exception):
    """给界面显示的友好错误。"""


@dataclass
class EngineConfig:
    base_url: str
    api_key: str
    model: str
    label: str
    json_mode: bool = True


def deepseek_config(api_key: str) -> EngineConfig:
    return EngineConfig(DEEPSEEK_BASE_URL, api_key, DEEPSEEK_MODEL, "DeepSeek 云端")


def ollama_config(model: Optional[str] = None) -> EngineConfig:
    # Ollama 不校验 key，但 openai SDK 要求非空
    return EngineConfig(OLLAMA_BASE_URL, "ollama", model or OLLAMA_MODEL, "本地 Ollama")


SYSTEM_PROMPT = """你是一名专业的会议纪要分析助手。你的任务是把杂乱的会议转写文本整理成结构化结果。

规则：
1. 忽略闲聊、寒暄、跑题内容，只保留与工作相关的信息。
2. summary：用 3-5 句中文概括会议的核心内容。
3. decisions：列出会议达成的关键决策或共识，每条一句话。
4. tasks：提取所有明确分工的待办事项。每个任务必须包含：
   - title：动宾结构的任务标题
   - assignee：负责人姓名（原文没有则填 "未指定"）
   - deadline：截止时间，尽量保留原文说法（如 "下周三前"），没有则填 "待定"
   - priority：High / Medium / Low 之一，依据紧急程度和对上线的影响判断
   - status：一律填 "To Do"
   - source_quote：逐字摘录支撑该任务的原文句子，不得改写或编造
5. 不得编造原文中不存在的任务、负责人或时间。

你必须只输出一个合法的 JSON 对象，不要输出任何其他文字或 Markdown。JSON 格式如下：
{
  "summary": "string",
  "decisions": ["string"],
  "tasks": [
    {
      "title": "string",
      "assignee": "string",
      "deadline": "string",
      "priority": "High | Medium | Low",
      "status": "To Do",
      "source_quote": "string"
    }
  ]
}"""


def _extract_json(text: str) -> dict:
    """JSON 解析兜底：先直接解析，再去掉 ```json 包裹，最后截取第一个 {...}。"""
    text = (text or "").strip()
    if not text:
        raise MeetingFlowError("模型返回了空内容，请重试。")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise MeetingFlowError("模型输出不是合法 JSON，已重试仍失败。可换用 DeepSeek 云端引擎再试。")


def _status_error_message(err: APIStatusError, cfg: EngineConfig) -> str:
    code = err.status_code
    if code == 401:
        return "API Key 无效（401）。请检查侧边栏中填写的 DeepSeek API Key 是否完整、正确。"
    if code == 402:
        return "账户余额不足（402）。请到 DeepSeek 开放平台充值后再试，或切换到本地 Ollama 模型。"
    if code == 404 and "ollama" in cfg.label.lower():
        return f"本地模型 `{cfg.model}` 不存在（404）。请先在命令行运行：ollama pull {cfg.model}"
    if code == 422:
        return "请求参数有误（422），请检查输入文本。"
    if code == 429:
        return "请求过于频繁（429），已达速率上限，请稍后再试。"
    if code >= 500:
        return f"{cfg.label} 服务端暂时不可用（{code}），请稍后重试。"
    return f"{cfg.label} 返回错误（{code}）：{err.message}"


def analyze_meeting(transcript: str, cfg: EngineConfig) -> MeetingAnalysis:
    """调用 LLM 分析会议文本，返回经 Pydantic 校验的结果。"""
    transcript = (transcript or "").strip()
    if not transcript:
        raise MeetingFlowError("会议文本为空，请先粘贴、上传或加载模拟会议纪要。")
    if not cfg.api_key:
        raise MeetingFlowError("未提供 DeepSeek API Key。请在侧边栏填写，或设置环境变量 DEEPSEEK_API_KEY。")

    # SDK 自带重试关掉，由下面的循环统一处理，便于区分可重试与不可重试的错误
    client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key, timeout=REQUEST_TIMEOUT, max_retries=0)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"以下是会议转写文本，请按要求输出 JSON：\n\n{transcript}"},
    ]
    kwargs = {"model": cfg.model, "messages": messages, "temperature": 0.2}
    if cfg.json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_error = "未知错误"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content
            data = _extract_json(content)
            return MeetingAnalysis.model_validate(data)

        except AuthenticationError as e:  # 401，重试无意义
            raise MeetingFlowError(_status_error_message(e, cfg)) from e
        except BadRequestError as e:  # 400
            raise MeetingFlowError(f"请求被拒绝（400）：{e.message}。文本可能过长，可删减后再试。") from e
        except RateLimitError as e:  # 429，退避后重试
            last_error = _status_error_message(e, cfg)
        except APITimeoutError:
            last_error = f"请求 {cfg.label} 超时（{REQUEST_TIMEOUT} 秒）。"
        except APIConnectionError:
            if "localhost" in cfg.base_url or "127.0.0.1" in cfg.base_url:
                raise MeetingFlowError(
                    "无法连接本地 Ollama。请确认已安装 Ollama for Windows 且托盘图标在运行，"
                    f"并已执行 `ollama pull {cfg.model}`。"
                )
            last_error = "网络连接失败，请检查网络或代理设置。"
        except APIStatusError as e:
            if e.status_code >= 500:
                last_error = _status_error_message(e, cfg)
            else:  # 402 / 404 / 422 等，重试无意义
                raise MeetingFlowError(_status_error_message(e, cfg)) from e
        except (MeetingFlowError, ValidationError) as e:  # JSON 或字段校验失败，重试一次可能就好
            last_error = f"模型输出格式不符合要求：{e}"

        if attempt < MAX_RETRIES:
            time.sleep(2 ** (attempt - 1))  # 1s, 2s

    raise MeetingFlowError(f"已重试 {MAX_RETRIES} 次仍失败：{last_error}")


def decode_text_file(raw: bytes) -> str:
    """解码上传的 .txt。Windows 记事本常见 UTF-8 带 BOM 或 GBK 编码，依次尝试。"""
    for enc in ("utf-8-sig", "gbk", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


MOCK_AUDIO_TRANSCRIPT = (
    "【模拟转写】王总：今天主要对齐一下新版本的进度。张工，支付 API 下周三前能调通吗？"
    "张工：可以，下周三前我把支付 API 调通。王总：好。另外大家注意，下周一上线前不再新增需求。"
)


def transcribe_audio(raw: bytes, suffix: str) -> tuple[str, bool]:
    """转写音频。返回 (文本, 是否真实转写)。未安装 faster-whisper 时返回模拟文本。"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return MOCK_AUDIO_TRANSCRIPT, False

    # Windows 上 NamedTemporaryFile 打开期间其他程序无法读取，所以 delete=False 并先关闭再读
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(raw)
        tmp.close()
        model = WhisperModel("small", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(tmp.name, language="zh", vad_filter=True)
        text = "".join(seg.text for seg in segments).strip()
        if not text:
            raise MeetingFlowError("音频中没有识别到语音内容。")
        return text, True
    except MeetingFlowError:
        raise
    except Exception as e:
        raise MeetingFlowError(f"音频转写失败：{e}") from e
    finally:
        try:
            os.remove(tmp.name)
        except OSError:
            pass
