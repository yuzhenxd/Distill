"""音频工具：统一成 16 kHz、单声道、16 位 PCM，并在停顿处切段。

DeepSeek 语音识别只接受 16 位 PCM WAV（或 Ogg Opus），单次请求不超过 120 秒、8 MiB。
"""
import io
import math
import wave
from array import array
from pathlib import Path

from .i18n import tr

SAMPLE_RATE = 16000
BYTES_PER_SEC = SAMPLE_RATE * 2
BLOCK_BYTES = BYTES_PER_SEC // 10  # 100 ms


class AudioError(Exception):
    pass


def to_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def rms(pcm: bytes) -> float:
    a = array("h")
    a.frombytes(pcm[: len(pcm) & ~1])
    if not a:
        return 0.0
    return math.sqrt(sum(x * x for x in a) / len(a))


def resample(pcm: bytes, from_rate: int) -> bytes:
    """麦克风不支持 16 kHz 时的兜底：按最近采样点换算，对语音识别足够。"""
    src = array("h")
    src.frombytes(pcm[: len(pcm) & ~1])
    ratio = from_rate / SAMPLE_RATE
    out = array("h", (src[int(i * ratio)] for i in range(int(len(src) / ratio))))
    return out.tobytes()


def split(pcm: bytes, max_s: float = 115, search_s: float = 10) -> list[bytes]:
    """把长音频切成不超过 max_s 秒的片段，切点选在最后 search_s 秒内最安静的 100 ms，尽量不切断句子。"""
    pieces = []
    limit = int(max_s * BYTES_PER_SEC)
    while len(pcm) > limit:
        start = int((max_s - search_s) * BYTES_PER_SEC) // BLOCK_BYTES
        end = limit // BLOCK_BYTES
        quietest = min(range(start, end), key=lambda i: rms(pcm[i * BLOCK_BYTES:(i + 1) * BLOCK_BYTES]))
        cut = quietest * BLOCK_BYTES
        pieces.append(pcm[:cut])
        pcm = pcm[cut:]
    if pcm:
        pieces.append(pcm)
    return pieces


def decode_file(path: Path) -> bytes:
    """把 mp3 / m4a / wav 等任意音频解码成 16 kHz 单声道 PCM。"""
    import av

    out = bytearray()
    try:
        with av.open(str(path)) as container:
            if not container.streams.audio:
                raise AudioError(tr("文件里没有音频轨道。"))
            resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
            for frame in container.decode(container.streams.audio[0]):
                for f in resampler.resample(frame):
                    out += bytes(f.planes[0])[: f.samples * 2]
            for f in resampler.resample(None):
                out += bytes(f.planes[0])[: f.samples * 2]
    except av.FFmpegError as e:
        raise AudioError(tr("无法解码音频文件：{error}", error=e)) from None
    return bytes(out)
