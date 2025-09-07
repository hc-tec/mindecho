from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()

# In-memory placeholder for settings.
# In a real application, this would come from a database or a config file.
app_settings = {
    "theme": "dark",
    "notifications_enabled": True,
    "ai_model": "gemini-2.5-flash-preview-05-20"
}

class Settings(BaseModel):
    theme: str
    notifications_enabled: bool
    ai_model: str

@router.get("/settings", response_model=Settings)
async def get_settings():
    """
    Get all application settings.
    """
    return app_settings

@router.put("/settings", response_model=Settings)
async def update_settings(settings: Settings):
    """
    Update application settings.
    """
    app_settings.update(settings.dict())
    return app_settings
