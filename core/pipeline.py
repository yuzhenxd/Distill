from pathlib import Path

from .config import Settings
from .i18n import tr
from .llm import analyze_transcript
from .transcriber import AUDIO_EXTS, TEXT_EXTS, Progress, TranscribeError, read_text_file, transcribe


def process_file(path: str, s: Settings, progress: Progress) -> dict:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in TEXT_EXTS:
        progress(15, tr("正在读取会议文本…"))
        transcript = read_text_file(p)
    elif ext in AUDIO_EXTS:
        transcript = transcribe(p, s, progress)
    else:
        raise TranscribeError(tr("不支持的文件格式：{name}", name=ext))
    return process_text(transcript, p.name, s, progress)


def process_text(transcript: str, source: str, s: Settings, progress: Progress) -> dict:
    if not transcript.strip():
        raise TranscribeError(tr("会议内容为空。"))
    progress(-1, tr("正在调用大模型提取摘要、关键决策与行动项…"))
    result = analyze_transcript(transcript, s)
    progress(100, tr("解析完成"))
    return {"source": source, "transcript": transcript, "result": result}
