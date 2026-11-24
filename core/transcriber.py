import json
import os
import ssl
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Callable

import certifi
import openai
from openai import OpenAI

from . import audio
from .config import Settings
from .i18n import tr

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
    raise TranscribeError(tr("无法识别文本文件编码，请另存为 UTF-8 后重试。"))


def check_ready(s: Settings) -> None:
    """开始转写前检查所选引擎是否可用，避免录了一段才报错。"""
    if s.whisper_mode == "deepseek" and not _deepseek_key(s):
        raise TranscribeError(tr("语音识别使用 DeepSeek，但尚未填写 DeepSeek API Key，请前往「设置」。"))
    if s.whisper_mode == "api" and not s.whisper_api_key:
        raise TranscribeError(tr("尚未填写 Whisper API Key，请前往「设置」配置。"))
    if s.whisper_mode == "local":
        _import_whisper()


def transcribe(path: Path, s: Settings, progress: Progress) -> str:
    if s.whisper_mode == "deepseek":
        return _transcribe_deepseek_file(path, s, progress)
    if s.whisper_mode == "api":
        return _transcribe_api(path, s, progress)
    return _transcribe_local(path, s, progress)


def transcribe_pcm(pcm: bytes, s: Settings) -> str:
    """转写一小段 16 kHz 单声道 PCM（实时翻译逐段调用）。"""
    if s.whisper_mode == "deepseek":
        return deepseek_asr(audio.to_wav(pcm), s)
    if s.whisper_mode == "api":
        return _whisper_api(("segment.wav", audio.to_wav(pcm)), s)
    import numpy as np  # faster-whisper 的依赖，装了它就有

    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768
    segments, _ = _local_model(s).transcribe(samples, language=s.language or None, vad_filter=True)
    return "".join(seg.text for seg in segments).strip()


def _fmt(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


# ---------- DeepSeek 语音识别 ----------
def _deepseek_key(s: Settings) -> str:
    return s.deepseek_api_key or os.environ.get("DEEPSEEK_API_KEY", "")


def deepseek_asr(wav: bytes, s: Settings) -> str:
    key = _deepseek_key(s)
    if not key:
        raise TranscribeError(tr("尚未填写 DeepSeek API Key，请前往「设置」。"))
    url = s.deepseek_base_url.rstrip("/").removesuffix("/v1") + "/v1/tools/asr"
    boundary = uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n"
    ).encode() + wav + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    try:
        # 打包后的 macOS 版找不到系统证书，用 certifi 自带的证书校验 HTTPS
        ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8")).get("text", "").strip()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise TranscribeError(tr("DeepSeek API Key 无效，请在设置页检查。")) from None
        raw = e.read().decode("utf-8", "replace")
        try:
            message = json.loads(raw)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = raw[:200]
        raise TranscribeError(tr("DeepSeek 语音识别返回错误（HTTP {code}）：{message}", code=e.code, message=message)) from None
    except TimeoutError:
        raise TranscribeError(tr("DeepSeek 语音识别超时，请稍后重试。")) from None
    except OSError:  # URLError 及网络中断
        raise TranscribeError(tr("无法连接到 DeepSeek 语音识别服务，请检查网络。")) from None


def _transcribe_deepseek_file(path: Path, s: Settings, progress: Progress) -> str:
    progress(5, tr("正在解码音频…"))
    try:
        pieces = audio.split(audio.decode_file(path))
    except audio.AudioError as e:
        raise TranscribeError(str(e)) from None
    texts = []
    for i, piece in enumerate(pieces, 1):
        progress(8 + int((i - 1) / len(pieces) * 52), tr("DeepSeek 正在转写第 {i} / {n} 段…", i=i, n=len(pieces)))
        text = deepseek_asr(audio.to_wav(piece), s)
        if text:
            texts.append(text)
    if not texts:
        raise TranscribeError(tr("没有从音频中识别到语音内容。"))
    progress(60, tr("转写完成"))
    return "\n".join(texts)


# ---------- 本地 faster-whisper ----------
def _import_whisper():
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise TranscribeError(tr(
            "未检测到本地转写引擎 faster-whisper。\n\n"
            "方案一：在「设置」中把转写方式切换为「DeepSeek 语音识别」；\n"
            "方案二：在终端执行 pip install faster-whisper，然后重启应用；\n"
            "方案三：直接上传会议文本（.txt / .md）。"
        )) from None
    return WhisperModel


def _local_model(s: Settings):
    WhisperModel = _import_whisper()
    size = s.whisper_model_size
    model = _model_cache.get(size)
    if model is None:
        try:
            model = WhisperModel(size, device="auto", compute_type="int8")
        except Exception as e:  # 模型下载失败、磁盘不足等，原因多样，统一转成可读提示
            raise TranscribeError(tr("Whisper 模型加载失败：{error}", error=e)) from None
        _model_cache[size] = model
    return model


def _transcribe_local(path: Path, s: Settings, progress: Progress) -> str:
    _import_whisper()
    progress(5, tr("正在加载 Whisper 模型（{size}），首次使用需要下载模型文件…", size=s.whisper_model_size))
    model = _local_model(s)

    progress(8, tr("正在识别语音…"))
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
                progress(pct, tr("正在转写音频… {pos} / {total}", pos=_fmt(seg.end), total=_fmt(duration)))
    except Exception as e:  # 音频损坏、解码失败
        raise TranscribeError(tr("音频转写失败：{error}", error=e)) from None

    if not lines:
        raise TranscribeError(tr("没有从音频中识别到语音内容。"))
    return "\n".join(lines)


# ---------- OpenAI 兼容 Whisper API ----------
def _whisper_api(file, s: Settings) -> str:
    if not s.whisper_api_key:
        raise TranscribeError(tr("尚未填写 Whisper API Key，请前往「设置」配置。"))
    client = OpenAI(api_key=s.whisper_api_key, base_url=s.whisper_base_url, timeout=600)
    extra = {"language": s.language} if s.language else {}
    try:
        result = client.audio.transcriptions.create(model=s.whisper_api_model, file=file, **extra)
    except openai.AuthenticationError:
        raise TranscribeError(tr("Whisper API Key 无效，请在设置页检查。")) from None
    except openai.OpenAIError as e:
        raise TranscribeError(tr("云端转写失败：{error}", error=e)) from None
    return result.text.strip()


def _transcribe_api(path: Path, s: Settings, progress: Progress) -> str:
    progress(10, tr("正在上传音频到云端 Whisper 转写…"))
    with path.open("rb") as f:
        text = _whisper_api(f, s)
    progress(60, tr("云端转写完成"))
    return text
