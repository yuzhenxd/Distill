"""实时转写与翻译：麦克风音频在停顿处切成短段，逐段识别、翻译，结果通过回调交给界面。

线程：PortAudio 回调只把音频放进队列；切段线程计算音量、决定切点；处理线程按顺序识别与翻译。
回调都在后台线程里调用，界面层需要用 Qt 信号转回主线程。
"""
import math
import queue
import threading
from typing import Callable

from . import audio
from .config import Settings
from .i18n import tr
from .llm import make_client, translate
from .transcriber import check_ready, transcribe_pcm

# 显示名 → 提示词里的语言名
TARGET_LANGUAGES = {
    "中文": "简体中文",
    "English": "英文",
    "日本語": "日文",
    "한국어": "韩文",
    "Français": "法文",
    "Deutsch": "德文",
    "Español": "西班牙文",
    "Русский": "俄文",
}

MIN_SEGMENT_S = 4     # 说话停顿时，至少攒够这么长才切段，避免句子太碎
MAX_SEGMENT_S = 15    # 一直不停顿时强制切段，保证译文跟得上
PAUSE_BLOCKS = 6      # 连续 0.6 秒低于说话音量视为停顿
SPEECH_FLOOR = 150    # 说话音量阈值的下限（16 位 PCM 的 RMS）
MUTED_BLOCKS = 20     # 开头连续 2 秒全是 0：真实麦克风总有底噪，全 0 说明系统没给权限或麦克风被静音


class LiveError(Exception):
    pass


def check_live_ready(s: Settings) -> None:
    check_ready(s)
    make_client(s)  # 翻译用的大模型未配置时这里会抛出 LLMError


def list_input_devices() -> tuple[list[tuple[int, str]], int | None]:
    """返回（[(设备序号, 名称)], 默认设备序号）。只列默认音频接口下的设备，避免 Windows 上同一个麦克风出现四五次。"""
    try:
        import sounddevice as sd
        hostapi = sd.default.hostapi
        devices = [
            (i, d["name"]) for i, d in enumerate(sd.query_devices())
            if d["max_input_channels"] > 0 and d["hostapi"] == hostapi
        ]
        default = sd.default.device[0]
    except (OSError, ImportError):  # 没有声卡驱动或 PortAudio 加载失败
        return [], None
    return devices, default if any(i == default for i, _ in devices) else None


class LiveSession:
    def __init__(
        self,
        s: Settings,
        target: str,
        device: int | None,
        on_level: Callable[[float], None],
        on_pending: Callable[[int], None],
        on_segment: Callable[[dict], None],
        on_error: Callable[[str], None],
        on_finished: Callable[[], None],
        on_muted: Callable[[], None],
    ):
        self.s = s
        self.target = TARGET_LANGUAGES.get(target, target)
        self.device = device
        self.on_level = on_level
        self.on_pending = on_pending
        self.on_segment = on_segment
        self.on_error = on_error
        self.on_finished = on_finished
        self.on_muted = on_muted
        self._audio: queue.Queue = queue.Queue()
        self._segments: queue.Queue = queue.Queue()
        self._stopping = threading.Event()
        self._pending = 0
        self._lock = threading.Lock()
        self._stream = None
        self._rate = audio.SAMPLE_RATE

    def start(self) -> None:
        try:
            import sounddevice as sd
        except (OSError, ImportError) as e:
            raise LiveError(tr("无法加载录音组件：{error}", error=e)) from None
        try:
            try:
                self._stream = self._open(sd, audio.SAMPLE_RATE)
            except sd.PortAudioError:  # 部分声卡不支持 16 kHz，改用设备默认采样率再换算
                rate = int(sd.query_devices(self.device, "input")["default_samplerate"])
                self._stream = self._open(sd, rate)
                self._rate = rate
            self._stream.start()
        except sd.PortAudioError as e:
            raise LiveError(tr("无法打开麦克风：{error}", error=e)) from None
        threading.Thread(target=self._segment_loop, daemon=True).start()
        threading.Thread(target=self._process_loop, daemon=True).start()

    def _open(self, sd, rate: int):
        return sd.RawInputStream(
            samplerate=rate, channels=1, dtype="int16", device=self.device,
            blocksize=rate // 10, callback=lambda data, *_: self._audio.put(bytes(data)),
        )

    def stop(self) -> None:
        """停止录音；最后一段处理完后调用 on_finished。"""
        if self._stopping.is_set():  # 用户点停止和静音检测可能先后触发
            return
        self._stream.stop()
        self._stream.close()
        self._stopping.set()

    # ---------- 切段线程 ----------
    def _segment_loop(self) -> None:
        blocks: list[tuple[bytes, float]] = []  # (100 ms 音频, 音量)
        floor = 0.0         # 背景噪音估计：快降慢升
        start_s = 0.0       # 当前缓冲在整场录音中的起始秒数
        silent = 0          # 开头连续全 0 的块数，听到任何声音后置为 -1 不再检查
        while True:
            try:
                block = self._audio.get(timeout=0.1)
            except queue.Empty:
                if self._stopping.is_set():
                    break
                continue
            if self._rate != audio.SAMPLE_RATE:
                block = audio.resample(block, self._rate)
            level = audio.rms(block)
            self.on_level(level)
            if silent >= 0:
                silent = silent + 1 if level == 0 else -1
                if silent == MUTED_BLOCKS:
                    self.on_muted()
            floor = level if level < floor or not floor else floor + (level - floor) * 0.01
            blocks.append((block, level))

            threshold = max(SPEECH_FLOOR, floor * 3)
            duration = len(blocks) / 10
            paused = all(lv < threshold for _, lv in blocks[-PAUSE_BLOCKS:])
            if duration >= MAX_SEGMENT_S:
                tail = range(len(blocks) - 50, len(blocks))  # 最后 5 秒里最安静的位置
                cut = min(tail, key=lambda i: blocks[i][1]) + 1
            elif duration >= MIN_SEGMENT_S and paused:
                cut = len(blocks)
            else:
                continue
            self._emit(blocks[:cut], start_s, threshold)
            start_s += cut / 10
            blocks = blocks[cut:]
        self._emit(blocks, start_s, max(SPEECH_FLOOR, floor * 3))
        self._segments.put(None)

    def _emit(self, blocks: list, start_s: float, threshold: float) -> None:
        # 至少 0.3 秒有人声才送去识别，纯静音段既浪费费用，也容易被识别出幻觉文字
        if sum(lv > threshold for _, lv in blocks) < 3:
            return
        with self._lock:
            self._pending += 1
            pending = self._pending
        self.on_pending(pending)
        self._segments.put((start_s, b"".join(b for b, _ in blocks)))

    # ---------- 识别与翻译线程 ----------
    def _process_loop(self) -> None:
        context: list[str] = []
        while (item := self._segments.get()) is not None:
            start_s, pcm = item
            try:
                self._process(start_s, pcm, context)
            except Exception as e:  # 线程边界：单段失败不影响后续录音
                self.on_error(str(e) or e.__class__.__name__)
            with self._lock:
                self._pending -= 1
                pending = self._pending
            self.on_pending(pending)
        self.on_finished()

    def _process(self, start_s: float, pcm: bytes, context: list[str]) -> None:
        text = transcribe_pcm(pcm, self.s)
        if not text:
            return
        try:
            translation = translate(text, self.target, context[-3:], self.s)
        except Exception as e:  # 翻译失败时保留原文
            translation = ""
            self.on_error(tr("翻译失败：{error}", error=e))
        context.append(text)
        self.on_segment({"start": round(start_s, 1), "text": text, "translation": translation})


def level_percent(rms: float) -> int:
    """音量 RMS → 0~100，按分贝刻度，-60 dB 以下为 0。"""
    if rms < 1:
        return 0
    return max(0, min(100, int((20 * math.log10(rms / 32768) + 60) / 60 * 100)))
