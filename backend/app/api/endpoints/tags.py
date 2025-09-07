from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from app.api import deps
from app.crud import crud_favorites

router = APIRouter()

class TagWithCount(BaseModel):
    name: str
    count: int

@router.get("/tags", response_model=List[TagWithCount])
async def read_tags_with_counts(
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Retrieve all tags with their usage counts.
    """
    tags_with_counts = await crud_favorites.tag.get_with_counts(db)
    return tags_with_counts
