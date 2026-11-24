from pathlib import Path
from typing import Callable

import openai
from openai import OpenAI

from .config import Settings

AUDIO_EXTS = {".mp3", ".wav", ".m4a"}
TEXT_EXTS = {".txt", ".md"}

Progress = Callable[[int, str], None]

_model_cache: dict = {}


class TranscribeError(Exception):
    pass


def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "gbk", "utf-16"):  # 兼容 Windows 记事本保存的 GBK / UTF-16
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise TranscribeError("无法识别文本文件编码，请另存为 UTF-8 后重试。")


def transcribe(path: Path, s: Settings, progress: Progress) -> str:
    if s.whisper_mode == "api":
        return _transcribe_api(path, s, progress)
    return _transcribe_local(path, s, progress)


def _fmt(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _transcribe_local(path: Path, s: Settings, progress: Progress) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise TranscribeError(
            "未检测到本地转写引擎 faster-whisper。\n\n"
            "方案一：在终端执行 pip install faster-whisper，然后重启应用；\n"
            "方案二：在「模型与 API 设置」中把转写方式切换为「云端 Whisper API」并填写 API Key；\n"
            "方案三：直接上传会议文本（.txt / .md）。"
        ) from None

    size = s.whisper_model_size
    progress(5, f"正在加载 Whisper 模型（{size}），首次使用需要下载模型文件…")
    model = _model_cache.get(size)
    if model is None:
        try:
            model = WhisperModel(size, device="auto", compute_type="int8")
        except Exception as e:  # 模型下载失败、磁盘不足等，原因多样，统一转成可读提示
            raise TranscribeError(f"Whisper 模型加载失败：{e}") from None
        _model_cache[size] = model

    progress(8, "正在识别语音…")
    try:
        segments, info = model.transcribe(str(path), language=s.language or None, vad_filter=True)
        duration = info.duration or 0
        lines = []
        for seg in segments:
            text = seg.text.strip()
            if text:
                lines.append(text)
            if duration:
                pct = 8 + int(min(seg.end / duration, 1) * 52)
                progress(pct, f"正在转写音频… {_fmt(seg.end)} / {_fmt(duration)}")
    except Exception as e:  # 音频损坏、解码失败
        raise TranscribeError(f"音频转写失败：{e}") from None

    if not lines:
        raise TranscribeError("没有从音频中识别到语音内容。")
    return "\n".join(lines)


def _transcribe_api(path: Path, s: Settings, progress: Progress) -> str:
    if not s.whisper_api_key:
        raise TranscribeError("尚未填写 Whisper API Key，请前往「模型与 API 设置」配置。")
    client = OpenAI(api_key=s.whisper_api_key, base_url=s.whisper_base_url, timeout=600)
    progress(10, "正在上传音频到云端 Whisper 转写…")
    extra = {"language": s.language} if s.language else {}
    try:
        with path.open("rb") as f:
            result = client.audio.transcriptions.create(model=s.whisper_api_model, file=f, **extra)
    except openai.AuthenticationError:
        raise TranscribeError("Whisper API Key 无效，请在设置页检查。") from None
    except openai.OpenAIError as e:
        raise TranscribeError(f"云端转写失败：{e}") from None
    progress(60, "云端转写完成")
    return result.text
