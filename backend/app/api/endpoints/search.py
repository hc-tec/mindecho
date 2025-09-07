from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from app.api import deps
from app.schemas.unified import FavoriteItemBrief, Result
from sqlalchemy import select, or_
from app.db.models import FavoriteItem, Result as ResultModel

router = APIRouter()

class SearchResults(BaseModel):
    collections: List[FavoriteItemBrief]
    results: List[Result]

@router.get("/search", response_model=SearchResults)
async def search_all(
    q: str = Query(..., min_length=2, description="Search query"),
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Perform a global search across collections and results.
    """
    # Search collections (FavoriteItem)
    collections_query = select(FavoriteItem).where(
        or_(
            FavoriteItem.title.ilike(f"%{q}%"),
            FavoriteItem.intro.ilike(f"%{q}%")
        )
    ).limit(20)
    collections_result = await db.execute(collections_query)
    collections = collections_result.scalars().all()
    
    # Search results
    results_query = select(ResultModel).where(
        ResultModel.content.ilike(f"%{q}%")
    ).limit(20)
    results_result = await db.execute(results_query)
    results = results_result.scalars().all()

    return {
        "collections": collections,
        "results": results,
    }
