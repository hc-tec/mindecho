from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()
from app.core.runtime_config import runtime_config
from app.core.config import AVAILABLE_AI_MODELS
from app.api import deps
from app.db.models import AppSetting

# In-memory placeholder for settings.
# In a real application, this would come from a database or a config file.
DEFAULT_SETTINGS = {
    "theme": "dark",
    "notifications_enabled": True,
    "ai_model": "gemini-2.5-flash-preview-05-20",
    "first_sync_threshold": 50  # Default threshold for first sync detection
}

class AIModelInfo(BaseModel):
    """AI模型信息"""
    id: str  # 模型ID
    name: str  # 显示名称
    provider: str  # 提供商（openai, google, anthropic等）
    description: str  # 描述信息
    requires_browser: bool  # 是否需要浏览器cookie
    supports_streaming: bool  # 是否支持流式输出
    max_tokens: int  # 最大token数
    is_default: bool  # 是否为默认模型


class Settings(BaseModel):
    theme: str
    notifications_enabled: bool
    ai_model: str
    first_sync_threshold: int = 50  # Items count threshold to skip AI processing on first sync
    category_to_workshop: Optional[Dict[str, str]] = None

async def _load_settings(db: AsyncSession) -> Dict[str, Any]:
    rows = (await db.execute(select(AppSetting))).scalars().all()
    data: Dict[str, Any] = dict(DEFAULT_SETTINGS)
    for row in rows:
        data[row.key] = row.value
    return data

async def _save_settings(db: AsyncSession, data: Dict[str, Any]) -> Dict[str, Any]:
    # upsert by key
    for key, value in data.items():
        existing = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalars().first()
        if existing:
            # store JSON for complex objects
            if isinstance(value, (dict, list)):
                import json
                existing.value = json.dumps(value, ensure_ascii=False)
            else:
                existing.value = str(value)
            db.add(existing)
        else:
            if isinstance(value, (dict, list)):
                import json
                db.add(AppSetting(key=key, value=json.dumps(value, ensure_ascii=False)))
            else:
                db.add(AppSetting(key=key, value=str(value)))
    await db.commit()
    return await _load_settings(db)

@router.get("/settings", response_model=Settings)
async def get_settings(db: AsyncSession = Depends(deps.get_db)):
    """
    Get all application settings.
    """
    settings_data = await _load_settings(db)
    return {
        **settings_data,
        "category_to_workshop": runtime_config.get_category_map(),
    }

@router.put("/settings", response_model=Settings)
async def update_settings(settings: Settings, db: AsyncSession = Depends(deps.get_db)):
    """
    Update application settings.
    """
    data = settings.dict()
    category_map = data.pop("category_to_workshop", None)
    # persist remaining settings
    await _save_settings(db, data)
    if category_map is not None:
        runtime_config.set_category_map(category_map)
    settings_data = await _load_settings(db)
    return {
        **settings_data,
        "category_to_workshop": runtime_config.get_category_map(),
    }


@router.get("/settings/ai-models", response_model=List[AIModelInfo])
async def get_available_ai_models():
    """
    获取所有可用的AI模型列表

    返回系统支持的所有AI模型配置，包括：
    - 模型ID和显示名称
    - 提供商信息
    - 功能特性（是否需要浏览器、是否支持流式输出等）
    - Token限制

    前端可以根据这些信息动态生成模型选择器
    """
    return AVAILABLE_AI_MODELS
