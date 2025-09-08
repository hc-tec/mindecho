from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.api import deps
from app.crud import crud_favorites
from app.schemas.unified import (
    FavoriteItem, PaginatedFavoriteItem, FavoriteItemCreate, FavoriteItemBrief,
    FavoriteItemUpdate
)
from app.db import models
from pydantic import BaseModel as PydanticBaseModel

router = APIRouter()

class IdsRequest(PydanticBaseModel):
    ids: List[int]

class TagsRequest(PydanticBaseModel):
    tags: List[str]

@router.get("", response_model=PaginatedFavoriteItem)
async def read_collections(
    db: AsyncSession = Depends(deps.get_db),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: str = Query("favorited_at", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
):
    """
    Retrieve a paginated list of collections (favorite items) with sorting and filtering.
    """
    tags_list = tags.split(',') if tags else None
    skip = (page - 1) * size
    
    # The actual filtering and sorting logic will be implemented in the CRUD layer next
    items, total = await crud_favorites.favorite_item.get_multi_paginated_with_filters(
        db,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
        tags=tags_list
    )
    
    return {"total": total, "items": items}

@router.post("/archive", status_code=status.HTTP_200_OK)
async def archive_collections(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: IdsRequest,
):
    """
    Archive a list of collections by their IDs.
    """
    if not request.ids:
        return {"message": "No collections to archive."}
    
    updated_count = await crud_favorites.favorite_item.update_status_bulk(
        db, ids=request.ids, status=models.FavoriteItemStatus.ARCHIVED
    )
    
    if updated_count != len(request.ids):
        raise HTTPException(
            status_code=404, 
            detail=f"Could not archive all items. Found and archived {updated_count} out of {len(request.ids)}."
        )

    return {"message": f"Successfully archived {updated_count} collections."}


@router.post("/delete", status_code=status.HTTP_200_OK)
async def delete_collections_bulk(
    *,
    db: AsyncSession = Depends(deps.get_db),
    request: IdsRequest,
):
    """
    Delete a list of collections by their IDs.
    """
    if not request.ids:
        return {"message": "No collections to delete."}

    deleted_count = await crud_favorites.favorite_item.remove_bulk(db, ids=request.ids)

    if deleted_count != len(request.ids):
        # This might happen if some IDs were not found.
        # It's not necessarily an error, but the client should be aware.
        return {
            "message": f"Deletion partially successful. Deleted {deleted_count} out of {len(request.ids)} collections.",
            "deleted_count": deleted_count,
        }

    return {"message": f"Successfully deleted {deleted_count} collections."}


@router.get("/inbox", response_model=PaginatedFavoriteItem)
async def read_inbox_collections(
    db: AsyncSession = Depends(deps.get_db),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    sort_by: str = Query("favorited_at", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
):
    """
    Retrieve a paginated list of collections with 'pending' status for the inbox view.
    """
    skip = (page - 1) * size
    
    items, total = await crud_favorites.favorite_item.get_multi_inbox(
        db,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    return {"total": total, "items": items}

@router.get("/{id}", response_model=FavoriteItem)
async def read_collection_by_id(
    id: int,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Retrieve a single collection (favorite item) by its unique database ID.
    """
    db_item = await crud_favorites.favorite_item.get_full(db, id=id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return db_item

@router.post("", response_model=FavoriteItem, status_code=201)
async def create_manual_collection(
    *,
    db: AsyncSession = Depends(deps.get_db),
    collection_in: FavoriteItemCreate,
):
    """
    Create a new collection (note) manually within the application.
    """
    # Here you might want to link to a default "manual" author/platform
    # For now, creating it directly
    new_collection = await crud_favorites.favorite_item.create(db, obj_in=collection_in)
    await db.commit()
    
    # We need to fetch it again to get all relations loaded
    created_collection = await crud_favorites.favorite_item.get_full(db, id=new_collection.id)
    return created_collection

@router.put("/{id}", response_model=FavoriteItem)
async def update_collection(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: int,
    collection_in: FavoriteItemUpdate,
):
    """
    Update a collection's metadata.
    """
    db_collection = await crud_favorites.favorite_item.get(db, id=id)
    if not db_collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    updated_collection = await crud_favorites.favorite_item.update(db, db_obj=db_collection, obj_in=collection_in)

    # Fetch again to get all relations loaded for the response
    return await crud_favorites.favorite_item.get_full(db, id=updated_collection.id)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: int,
):
    """
    Delete a collection.
    """
    db_collection = await crud_favorites.favorite_item.get(db, id=id)
    if not db_collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    await crud_favorites.favorite_item.remove(db, id=id)
    return

@router.post("/{id}/tags", response_model=FavoriteItem)
async def add_tags_to_collection(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: int,
    tags_in: TagsRequest,
):
    """
    Add one or more tags to a specific collection.
    """
    success = await crud_favorites.favorite_item.add_tags(db, item_id=id, tag_names=tags_in.tags)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # Re-fetch the full item to ensure all relations are loaded for the response
    return await crud_favorites.favorite_item.get_full(db, id=id)

@router.delete("/{id}/tags", response_model=FavoriteItem)
async def remove_tags_from_collection(
    *,
    db: AsyncSession = Depends(deps.get_db),
    id: int,
    tags_in: TagsRequest,
):
    """
    Remove one or more tags from a specific collection.
    """
    success = await crud_favorites.favorite_item.remove_tags(db, item_id=id, tag_names=tags_in.tags)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Re-fetch the full item to ensure all relations are loaded for the response
    return await crud_favorites.favorite_item.get_full(db, id=id)
