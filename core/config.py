import json
import os
from dataclasses import asdict, dataclass, fields

from .paths import data_dir

SETTINGS_FILE = data_dir() / "settings.json"


@dataclass
class Settings:
    provider: str = "deepseek"  # deepseek | ollama
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "qwen2.5:7b"
    whisper_mode: str = "deepseek"  # deepseek | local | api
    whisper_model_size: str = "small"
    whisper_api_key: str = ""
    whisper_base_url: str = "https://api.openai.com/v1"
    whisper_api_model: str = "whisper-1"
    language: str = "zh"  # 空字符串表示自动检测
    feishu_webhook: str = ""
    translate_target: str = "English"  # 实时翻译的目标语言，取 core.live.TARGET_LANGUAGES 的键
    theme: str = "light"  # 配色方案：light 日间 | dark 夜间
    ui_language: str = "zh"  # 界面语言：zh 中文 | en English（与上面的会议语言 language 无关）


def load_settings() -> Settings:
    if not SETTINGS_FILE.exists():
        return Settings()
    try:
        raw = json.loads(SETTINGS_FILE.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    known = {f.name for f in fields(Settings)}
    return Settings(**{k: v for k, v in raw.items() if k in known})


def save_settings(settings: Settings) -> None:
    SETTINGS_FILE.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), "utf-8")
    try:
        os.chmod(SETTINGS_FILE, 0o600)  # 文件里有 API Key，只允许当前用户读写
    except OSError:
        pass
