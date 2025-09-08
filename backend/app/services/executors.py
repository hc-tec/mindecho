import asyncio
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging_config import get_logger
from app.db.models import FavoriteItem, Workshop as WorkshopModel
from client_sdk.rpc_client import EAIRPCClient
from app.core.config import settings

logger = get_logger(__name__)

class ExecutionContext:
    def __init__(self, db: AsyncSession, task_id: int, favorite_item_id: int) -> None:
        self.db = db
        self.task_id = task_id
        self.favorite_item_id = favorite_item_id


async def _build_source_text(db: AsyncSession, favorite_item_id: int) -> str:
    source = ""
    item = await db.get(FavoriteItem, favorite_item_id)
    if item:
        title = item.title or ""
        intro = item.intro or ""
        source = f"Title: {title}\nIntro: {intro}".strip()
    return source


async def execute_llm_chat(ctx: ExecutionContext, *, prompt_template: str, model: Optional[str]) -> str:
    prompt_template = prompt_template
    source = await _build_source_text(ctx.db, ctx.favorite_item_id)
    prompt = prompt_template.replace("{source}", source)

    client = EAIRPCClient(base_url=settings.EAI_BASE_URL, api_key=settings.EAI_API_KEY)
    try:
        await client.start()
        result = await (client.chat_with_yuanbao(prompt=prompt, model=model) if model else client.chat_with_yuanbao(prompt=prompt))
        return result.get("text", "") or ""
    except Exception as e:
        logger.error(e)
    finally:
        await client.stop()


Executor = Any


class ExecutorRegistry:
    def __init__(self) -> None:
        self._executors: Dict[str, Executor] = {
            "llm_chat": execute_llm_chat,
        }

    def get(self, executor_type: str) -> Executor:
        return self._executors.get(executor_type, execute_llm_chat)


executor_registry = ExecutorRegistry()


