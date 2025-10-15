from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .base import CRUDBase
from app.db.models import Workshop as WorkshopModel
from app.schemas.unified import WorkshopCreate, WorkshopUpdate, Workshop as WorkshopSchema


class CRUDWorkshop(CRUDBase[WorkshopModel, WorkshopCreate, WorkshopUpdate]):
    async def get_by_workshop_id(self, db: AsyncSession, *, workshop_id: str) -> Optional[WorkshopModel]:
        """Fetch a single workshop by its slug-like workshop_id."""
        result = await db.execute(select(self.model).where(self.model.workshop_id == workshop_id))
        return result.scalars().first()

workshop = CRUDWorkshop(WorkshopModel)
