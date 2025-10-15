from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.models import Collection
from app.crud.base import CRUDBase
from app.schemas.unified import CollectionCreate, CollectionUpdate


class CRUDCollection(CRUDBase[Collection, CollectionCreate, CollectionUpdate]):
    async def get_multi_with_pagination(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        platform: Optional[str] = None,
    ) -> Tuple[List[Collection], int]:
        """
        Get multiple Collection records with pagination and optional platform filter.

        Returns:
            Tuple of (collections list, total count)
        """
        query = (
            select(Collection)
            .options(
                selectinload(Collection.author),
            )
        )

        if platform:
            query = query.where(Collection.platform == platform)

        # Count query
        count_query = select(func.count()).select_from(Collection)
        if platform:
            count_query = count_query.where(Collection.platform == platform)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Order by title and apply pagination
        query = query.order_by(Collection.title.asc()).offset(skip).limit(limit)

        result = await db.execute(query)
        collections = result.scalars().all()

        return list(collections), total

    async def get_by_platform_collection_id(
        self,
        db: AsyncSession,
        *,
        platform_collection_id: str,
        platform: str,
    ) -> Optional[Collection]:
        """Get a collection by its platform-specific ID."""
        query = (
            select(Collection)
            .where(
                Collection.platform_collection_id == platform_collection_id,
                Collection.platform == platform,
            )
            .options(selectinload(Collection.author))
        )
        result = await db.execute(query)
        return result.scalars().first()


collection = CRUDCollection(Collection)
