from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base import CRUDBase
from app.db import models
from app.schemas.unified import TaskCreate, Task as TaskSchema


class CRUDTask(CRUDBase[models.Task, TaskCreate, TaskSchema]):
    async def get_unfinished_task_for_item(self, db: AsyncSession, *, favorite_item_id: int) -> Optional[models.Task]:
        """
        Checks if an unfinished (PENDING or IN_PROGRESS) task already exists
        for a given favorite item.
        """
        result = await db.execute(
            select(self.model).where(
                self.model.favorite_item_id == favorite_item_id,
                self.model.status.in_([models.TaskStatus.PENDING, models.TaskStatus.IN_PROGRESS]),
            )
        )
        return result.scalars().first()

    async def create_task(self, db: AsyncSession, *, task_in: TaskCreate) -> models.Task:
        """Wrapper around standard create for clarity in service layer."""
        return await self.create(db, obj_in=task_in)


task = CRUDTask(models.Task)
