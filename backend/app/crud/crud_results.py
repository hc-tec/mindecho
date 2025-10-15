from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .base import CRUDBase
from app.db import models
from app.schemas.unified import ResultCreate, Result as ResultSchema


class CRUDResult(CRUDBase[models.Result, ResultCreate, ResultSchema]):
    async def create_or_update(
        self,
        db: AsyncSession,
        *,
        workshop_id: str,
        favorite_item_id: int,
        task_id: int,
        content: str,
        existing_id: Optional[int] = None,
    ) -> models.Result:
        if existing_id is not None:
            existing = await db.get(models.Result, existing_id)
            if existing:
                existing.content = content
                existing.task_id = task_id
                db.add(existing)
                await db.commit()  # Commit to persist changes
                await db.refresh(existing)
                return existing
        # else create
        obj = models.Result(
            workshop_id=workshop_id,
            content=content,
            favorite_item_id=favorite_item_id,
            task_id=task_id,
        )
        db.add(obj)
        await db.commit()  # Commit to persist changes
        await db.refresh(obj)
        return obj


result = CRUDResult(models.Result)
