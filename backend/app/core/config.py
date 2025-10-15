from dataclasses import field
from typing import List

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./mindecho1.db"
    EAI_BASE_URL: str = "http://127.0.0.1:8008"
    EAI_API_KEY: str = "testkey"
    BILIBILI_FAVORITES_PLUGIN_ID: str = "bilibili_collection_videos"
    BILIBILI_FAVORITES_STREAM_GROUP: str = "bilibili_collection_videos-updates"
    BILIBILI_FAVORITES_STREAM_INTERVAL: int = 120
    BILIBILI_COOKIE_IDS: list[str] = field(default_factory=lambda :["23d87982-a801-4d12-ae93-50a85e336e98"])
    BILIBILI_FINGERPRINT_FIELDS: list[str] = field(default_factory=lambda :["id", "bvid"])
    BILIBILI_CLOSE_PAGE_WHEN_TASK_FINISHED: bool = True

    YUANBAO_COOKIE_IDS: list[str] = field(default_factory=lambda: ["31cfb23b-ade9-41ca-80ce-7624979cb006"])
    YUANBAO_CONVERSATION_ID: str = "565db7d0-cead-4cf2-b2ca-78d5d34de14c"

    # Xiaohongshu configuration
    XIAOHONGSHU_COOKIE_IDS: list[str] = field(default_factory=lambda : ["5bea8c40-8065-4e4f-bd1f-8fa0e3147a51"])
    XIAOHONGSHU_FAVORITES_PLUGIN_ID: str = "xiaohongshu_favorites_brief"
    XIAOHONGSHU_STREAM_INTERVAL: int = 120

    class Config:
        env_file = ".env"

settings = Settings()
