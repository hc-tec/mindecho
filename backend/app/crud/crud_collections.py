from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models import FavoriteItem, Tag

async def get_multi_with_filters(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "favorited_at",
    sort_order: str = "desc",
    tags: Optional[List[str]] = None
) -> List[FavoriteItem]:
    """
    Get multiple FavoriteItem records with advanced filtering and sorting.
    """
    query = (
        select(FavoriteItem)
        .options(
            selectinload(FavoriteItem.author),
            selectinload(FavoriteItem.collection),
            selectinload(FavoriteItem.tags),
            selectinload(FavoriteItem.results),
            selectinload(FavoriteItem.bilibili_video_details),
        )
    )

    if tags:
        query = query.join(FavoriteItem.tags).where(Tag.name.in_(tags))

    sort_column = getattr(FavoriteItem, sort_by, FavoriteItem.favorited_at)
    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    # Use unique() to handle potential duplicates from the join with tags
    return result.scalars().unique().all()
