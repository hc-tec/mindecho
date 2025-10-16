from dataclasses import field
from typing import List

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./mindecho2.db"
    EAI_BASE_URL: str = "http://127.0.0.1:8008"
    EAI_API_KEY: str = "testkey"
    BILIBILI_FAVORITES_PLUGIN_ID: str = "bilibili_collection_videos"
    BILIBILI_FAVORITES_STREAM_GROUP: str = "bilibili_collection_videos-updates"
    BILIBILI_FAVORITES_STREAM_INTERVAL: int = 120
    BILIBILI_COOKIE_IDS: list[str] = field(default_factory=lambda :["23d87982-a801-4d12-ae93-50a85e336e98"])
    BILIBILI_FINGERPRINT_FIELDS: list[str] = field(default_factory=lambda :["id", "bvid"])
    BILIBILI_CLOSE_PAGE_WHEN_TASK_FINISHED: bool = True
    BILIBILI_DETAILS_MAX_RETRY_ATTEMPTS: int = 5  # Max retry attempts for details fetch

    YUANBAO_COOKIE_IDS: list[str] = field(default_factory=lambda: ["0bf3d999-da6d-468e-8a70-77f08b5c68ed"])
    YUANBAO_CONVERSATION_ID: str = "565db7d0-cead-4cf2-b2ca-78d5d34de14c"

    # Xiaohongshu configuration
    XIAOHONGSHU_COOKIE_IDS: list[str] = field(default_factory=lambda : ["5bea8c40-8065-4e4f-bd1f-8fa0e3147a51"])
    XIAOHONGSHU_FAVORITES_PLUGIN_ID: str = "xiaohongshu_favorites_brief"
    XIAOHONGSHU_STREAM_INTERVAL: int = 120
    XIAOHONGSHU_FINGERPRINT_FIELDS: list[str] = field(default_factory=lambda: ["id"])

    # Stream event processing configuration
    FIRST_SYNC_THRESHOLD: int = 50  # Items count threshold to detect first sync
    XIAOHONGSHU_DETAILS_RETRY_DELAY_MINUTES: int = 5  # Retry delay for failed details fetch
    XIAOHONGSHU_DETAILS_MAX_RETRY_ATTEMPTS: int = 5  # Max retry attempts per note

    # SMTP Email configuration (for email notifications)
    SMTP_HOST: str = "smtp.gmail.com"  # SMTP server host
    SMTP_PORT: int = 587  # SMTP server port (587 for TLS, 465 for SSL)
    SMTP_USER: str = ""  # SMTP username (usually your email)
    SMTP_PASSWORD: str = ""  # SMTP password or app-specific password
    EMAIL_FROM: str = ""  # Sender email address (defaults to SMTP_USER)
    EMAIL_TO: str = ""  # Recipient email address

    class Config:
        env_file = ".env"

settings = Settings()


# ============================================================================
# AI模型配置
# ============================================================================

# 可用的AI模型列表，支持多种LLM提供商
# 用户可以在设置中选择使用哪个模型
AVAILABLE_AI_MODELS = [
    {
        "id": "yuanbao-chat",
        "name": "元宝",
        "provider": "yuanbao",
        "description": "腾讯的AI助手，适合中文对话",
        "requires_browser": True,  # 需要浏览器cookie
        "supports_streaming": True,
        "max_tokens": 4096,
        "is_default": True
    },
    {
        "id": "gemini-2.0-flash-exp",
        "name": "Gemini 2.0 Flash Experimental",
        "provider": "google",
        "description": "Google最新实验性模型，速度快，支持多模态",
        "requires_browser": False,
        "supports_streaming": True,
        "max_tokens": 1000000,  # 1M context window
        "is_default": False
    },
    {
        "id": "gemini-2.5-flash-preview-05-20",
        "name": "Gemini 2.5 Flash Preview",
        "provider": "google",
        "description": "Google Gemini 2.5预览版，平衡性能与速度",
        "requires_browser": False,
        "supports_streaming": True,
        "max_tokens": 1000000,
        "is_default": False
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4 Omni",
        "provider": "openai",
        "description": "OpenAI最新多模态模型，理解力强",
        "requires_browser": False,
        "supports_streaming": True,
        "max_tokens": 128000,
        "is_default": False
    },
    {
        "id": "gpt-4-turbo",
        "name": "GPT-4 Turbo",
        "provider": "openai",
        "description": "OpenAI高性能模型，适合复杂任务",
        "requires_browser": False,
        "supports_streaming": True,
        "max_tokens": 128000,
        "is_default": False
    },
    {
        "id": "claude-3-opus",
        "name": "Claude 3 Opus",
        "provider": "anthropic",
        "description": "Anthropic旗舰模型，擅长长文本分析",
        "requires_browser": False,
        "supports_streaming": True,
        "max_tokens": 200000,
        "is_default": False
    },
    {
        "id": "claude-3-sonnet",
        "name": "Claude 3 Sonnet",
        "provider": "anthropic",
        "description": "Anthropic平衡型模型，性价比高",
        "requires_browser": False,
        "supports_streaming": True,
        "max_tokens": 200000,
        "is_default": False
    },
    {
        "id": "deepseek-chat",
        "name": "DeepSeek Chat",
        "provider": "deepseek",
        "description": "DeepSeek对话模型，中文能力强",
        "requires_browser": False,
        "supports_streaming": True,
        "max_tokens": 32000,
        "is_default": False
    }
]
