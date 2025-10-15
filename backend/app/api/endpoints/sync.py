from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List

from app.api import deps
from app.services import favorites_service
from app.schemas.unified import Collection, FavoriteItem
from app.crud import collection as crud_collection

router = APIRouter()

# --- Request Models ---

class SyncCollectionsRequest(BaseModel):
    max_collections: Optional[int] = Field(None, description="Maximum number of collections to sync.")

class SyncVideosInCollectionRequest(BaseModel):
    max_videos: Optional[int] = Field(None, description="Maximum number of videos to sync from the collection.")

class SyncVideoDetailsRequest(BaseModel):
    bvids: List[str] = Field(..., description="A list of Bilibili video BV-IDs to sync details for.")

class SyncNoteDetailsRequest(BaseModel):
    note_ids: List[str] = Field(..., description="A list of Xiaohongshu note IDs to sync details for.")

class SyncNotesInCollectionRequest(BaseModel):
    max_notes: Optional[int] = Field(None, description="Maximum number of notes to sync from the collection.")

# --- Response Models ---

class SyncCollectionsResponse(BaseModel):
    message: str
    synced_collections_count: int
    collections: List[Collection]

class SyncVideosInCollectionResponse(BaseModel):
    message: str
    synced_videos_count: int
    videos: List[FavoriteItem]

class SyncVideoDetailsResponse(BaseModel):
    message: str
    updated_videos_count: int
    videos: List[FavoriteItem]

class SyncNotesInCollectionResponse(BaseModel):
    message: str
    synced_notes_count: int
    notes: List[FavoriteItem]

class SyncNoteDetailsResponse(BaseModel):
    message: str
    updated_notes_count: int
    notes: List[FavoriteItem]

class PaginatedCollectionsResponse(BaseModel):
    total: int
    items: List[Collection]

# --- API Endpoints ---

@router.get("/sync/collections", response_model=PaginatedCollectionsResponse)
async def get_collections_list(
    db: AsyncSession = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    platform: Optional[str] = None,
):
    """
    Get list of synced Collections (收藏夹).
    """
    collections, total = await crud_collection.get_multi_with_pagination(
        db, skip=skip, limit=limit, platform=platform
    )
    return {"total": total, "items": collections}

@router.post("/sync/bilibili/collections", response_model=SyncCollectionsResponse)
async def sync_bilibili_collections(
    sync_request: SyncCollectionsRequest,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Synchronize the user's Bilibili collection list.
    """
    try:
        synced_collections = await favorites_service.sync_bilibili_collections_list(
            db=db,
            max_collections=sync_request.max_collections
        )
        return {
            "message": "Collections synchronized successfully.",
            "synced_collections_count": len(synced_collections),
            "collections": synced_collections
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/bilibili/collections/{platform_collection_id}/videos", response_model=SyncVideosInCollectionResponse)
async def sync_videos_in_collection(
    platform_collection_id: str,
    sync_request: SyncVideosInCollectionRequest,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Synchronize the list of videos within a specific Bilibili collection.
    """
    try:
        synced_videos = await favorites_service.sync_videos_in_bilibili_collection(
            db=db,
            platform_collection_id=platform_collection_id,
            max_videos=sync_request.max_videos
        )
        return {
            "message": f"Videos for collection {platform_collection_id} synchronized successfully.",
            "synced_videos_count": len(synced_videos),
            "videos": synced_videos
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/bilibili/videos/details", response_model=SyncVideoDetailsResponse)
async def sync_video_details(
    sync_request: SyncVideoDetailsRequest,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Synchronize the full details for a given list of Bilibili videos (by bvid).
    """
    if not sync_request.bvids:
        raise HTTPException(status_code=400, detail="List of bvids cannot be empty.")
    try:
        updated_videos = await favorites_service.sync_bilibili_videos_details(
            db=db,
            bvids=sync_request.bvids
        )
        return {
            "message": "Video details updated successfully.",
            "updated_videos_count": len(updated_videos),
            "videos": updated_videos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Xiaohongshu Sync Endpoints
# ============================================================================

@router.post("/sync/xiaohongshu/collections", response_model=SyncCollectionsResponse)
async def sync_xiaohongshu_collections(
    sync_request: SyncCollectionsRequest,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Synchronize the user's Xiaohongshu collection list.
    """
    try:
        synced_collections = await favorites_service.sync_xiaohongshu_collections_list(
            db=db,
            max_collections=sync_request.max_collections
        )
        return {
            "message": "Xiaohongshu collections synchronized successfully.",
            "synced_collections_count": len(synced_collections),
            "collections": synced_collections
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/xiaohongshu/collections/{platform_collection_id}/notes", response_model=SyncNotesInCollectionResponse)
async def sync_notes_in_xiaohongshu_collection(
    platform_collection_id: str,
    sync_request: SyncNotesInCollectionRequest,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Synchronize the list of notes within a specific Xiaohongshu collection.
    """
    try:
        synced_notes = await favorites_service.sync_notes_in_xiaohongshu_collection(
            db=db,
            platform_collection_id=platform_collection_id,
            max_notes=sync_request.max_notes
        )
        return {
            "message": f"Notes for Xiaohongshu collection {platform_collection_id} synchronized successfully.",
            "synced_notes_count": len(synced_notes),
            "notes": synced_notes
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/xiaohongshu/notes/details", response_model=SyncNoteDetailsResponse)
async def sync_xiaohongshu_note_details(
    sync_request: SyncNoteDetailsRequest,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Synchronize the full details for a given list of Xiaohongshu notes (by note_id).
    """
    if not sync_request.note_ids:
        raise HTTPException(status_code=400, detail="List of note_ids cannot be empty.")
    try:
        updated_notes = await favorites_service.sync_xiaohongshu_notes_details(
            db=db,
            note_ids=sync_request.note_ids
        )
        return {
            "message": "Xiaohongshu note details updated successfully.",
            "updated_notes_count": len(updated_notes),
            "notes": updated_notes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
