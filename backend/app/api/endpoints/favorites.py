from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.crud import crud_favorites
from app.schemas.unified import PaginatedFavoriteItem

router = APIRouter()

@router.get("/favorites/", response_model=PaginatedFavoriteItem)
async def read_favorite_items(
    db: AsyncSession = Depends(deps.get_db),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
):
    """
    Retrieve favorite items with pagination.
    """
    skip = (page - 1) * size
    items, total = await crud_favorites.favorite_item.get_multi_paginated_with_filters(db, skip=skip, limit=size)
    return {"total": total, "items": items}
