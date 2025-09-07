from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List

from app.api import deps
from app.services import favorites_service
from app.schemas.unified import Collection, FavoriteItem

router = APIRouter()

# --- Request Models ---

class SyncCollectionsRequest(BaseModel):
    max_collections: Optional[int] = Field(None, description="Maximum number of collections to sync.")

class SyncVideosInCollectionRequest(BaseModel):
    max_videos: Optional[int] = Field(None, description="Maximum number of videos to sync from the collection.")

class SyncVideoDetailsRequest(BaseModel):
    bvids: List[str] = Field(..., description="A list of Bilibili video BV-IDs to sync details for.")

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

# --- API Endpoints ---

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
