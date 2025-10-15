from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.db.models import PlatformEnum, ItemTypeEnum, FavoriteItemStatus, TaskStatus


class ResultBase(BaseModel):
    workshop_id: str
    content: Optional[str] = None


class TaskBase(BaseModel):
    workshop_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    prompt: Optional[str] = None
    llm_model: Optional[str] = None


class TaskCreate(TaskBase):
    favorite_item_id: int


# Workshop Schemas
class WorkshopBase(BaseModel):
    workshop_id: str
    name: str
    description: Optional[str] = None
    default_prompt: str
    default_model: Optional[str] = None
    executor_type: str = "llm_chat"
    executor_config: Optional[dict] = None

class WorkshopCreate(WorkshopBase):
    pass

class WorkshopUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_prompt: Optional[str] = None
    default_model: Optional[str] = None
    executor_type: Optional[str] = None
    executor_config: Optional[dict] = None

class Workshop(WorkshopBase):
    id: int
    class Config:
        orm_mode = True


class ResultCreate(ResultBase):
    pass


class Result(ResultBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


# --- Media URL Schemas ---
class BilibiliVideoUrlBase(BaseModel):
    platform_media_id: Optional[int] = None
    base_url: Optional[str] = None
    backup_url: Optional[str] = None
    bandwidth: Optional[int] = None
    mime_type: Optional[str] = None
    codecs: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    frame_rate: Optional[str] = None

class BilibiliVideoUrlCreate(BilibiliVideoUrlBase):
    pass

class BilibiliVideoUrl(BilibiliVideoUrlBase):
    id: int
    class Config:
        orm_mode = True

class BilibiliAudioUrlBase(BaseModel):
    platform_media_id: Optional[int] = None
    base_url: Optional[str] = None
    backup_url: Optional[str] = None
    bandwidth: Optional[int] = None
    mime_type: Optional[str] = None
    codecs: Optional[str] = None

class BilibiliAudioUrlCreate(BilibiliAudioUrlBase):
    pass

class BilibiliAudioUrl(BilibiliAudioUrlBase):
    id: int
    class Config:
        orm_mode = True

# --- Subtitle Schema ---
class BilibiliSubtitleBase(BaseModel):
    sid: Optional[int] = None
    lang: Optional[str] = None
    content: Optional[str] = None
    from_sec: Optional[float] = None
    to_sec: Optional[float] = None

class BilibiliSubtitleCreate(BilibiliSubtitleBase):
    pass

class BilibiliSubtitle(BilibiliSubtitleBase):
    id: int
    class Config:
        orm_mode = True
        allow_population_by_field_name = True

# --- Main Entity Schemas ---

# Base Schemas (common attributes)
class TagBase(BaseModel):
    name: str

class AuthorBase(BaseModel):
    platform_user_id: str
    platform: PlatformEnum
    username: str
    avatar_url: Optional[str] = None

class CollectionBase(BaseModel):
    platform_collection_id: str
    platform: PlatformEnum
    title: str
    description: Optional[str] = None
    cover_url: Optional[str] = None
    item_count: int

class BilibiliVideoDetailBase(BaseModel):
    bvid: str
    duration_sec: int
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    coin_count: Optional[int] = None
    favorite_count: Optional[int] = None
    reply_count: Optional[int] = None
    share_count: Optional[int] = None
    danmaku_count: Optional[int] = None
    tname: Optional[str] = None
    tname_v2: Optional[str] = None
    dimension_width: Optional[int] = None
    dimension_height: Optional[int] = None
    dimension_rotate: Optional[int] = None

class FavoriteItemBase(BaseModel):
    platform_item_id: str
    platform: PlatformEnum
    item_type: ItemTypeEnum
    title: str
    intro: Optional[str] = None
    cover_url: Optional[str] = None
    published_at: Optional[datetime] = None
    favorited_at: datetime
    status: FavoriteItemStatus = FavoriteItemStatus.PENDING

# Schemas for creation (used in POST/PUT requests)
class TagCreate(TagBase):
    pass

class AuthorCreate(AuthorBase):
    pass

class CollectionCreate(CollectionBase):
    author_id: Optional[int] = None

class CollectionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    cover_url: Optional[str] = None
    item_count: Optional[int] = None

class BilibiliVideoDetailCreate(BilibiliVideoDetailBase):
    video_url: Optional[BilibiliVideoUrlCreate] = None
    audio_url: Optional[BilibiliAudioUrlCreate] = None
    subtitles: List[BilibiliSubtitleCreate] = []

class FavoriteItemCreate(FavoriteItemBase):
    # This is for creating the brief item. Details are added later.
    bilibili_video_details: Optional[BilibiliVideoDetailCreate] = None

class FavoriteItemUpdate(BaseModel):
    title: Optional[str] = None
    intro: Optional[str] = None
    status: Optional[FavoriteItemStatus] = None

# Schemas for reading data from DB (includes DB-generated fields like ID)
class Tag(TagBase):
    id: int
    class Config:
        orm_mode = True

class Author(AuthorBase):
    id: int
    class Config:
        orm_mode = True

class Collection(CollectionBase):
    id: int
    author: Optional[Author] = None
    class Config:
        orm_mode = True

class BilibiliVideoUrl(BilibiliVideoUrlBase):
    id: int
    class Config:
        orm_mode = True

class BilibiliAudioUrl(BilibiliAudioUrlBase):
    id: int
    class Config:
        orm_mode = True

class BilibiliSubtitle(BilibiliSubtitleBase):
    id: int
    class Config:
        orm_mode = True

class BilibiliVideoDetail(BilibiliVideoDetailBase):
    id: int
    video_url: Optional[BilibiliVideoUrl] = None
    audio_url: Optional[BilibiliAudioUrl] = None
    subtitles: List[BilibiliSubtitle] = []
    class Config:
        orm_mode = True


# ============================================================================
# Xiaohongshu Schemas
# ============================================================================

class XiaohongshuNoteImageBase(BaseModel):
    image_url: str
    order_index: int = 0

class XiaohongshuNoteImageCreate(XiaohongshuNoteImageBase):
    pass

class XiaohongshuNoteImage(XiaohongshuNoteImageBase):
    id: int
    class Config:
        orm_mode = True


class XiaohongshuNoteVideoBase(BaseModel):
    video_url: Optional[str] = None
    duration: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_url: Optional[str] = None

class XiaohongshuNoteVideoCreate(XiaohongshuNoteVideoBase):
    pass

class XiaohongshuNoteVideo(XiaohongshuNoteVideoBase):
    id: int
    class Config:
        orm_mode = True


class XiaohongshuNoteDetailBase(BaseModel):
    note_id: str
    xsec_token: Optional[str] = None
    desc: Optional[str] = None
    ip_location: Optional[str] = None
    published_date: Optional[str] = None
    like_count: Optional[int] = None
    collect_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    fetched_timestamp: Optional[str] = None

class XiaohongshuNoteDetailCreate(XiaohongshuNoteDetailBase):
    images: List[XiaohongshuNoteImageCreate] = []
    video: Optional[XiaohongshuNoteVideoCreate] = None

class XiaohongshuNoteDetail(XiaohongshuNoteDetailBase):
    id: int
    images: List[XiaohongshuNoteImage] = []
    video: Optional[XiaohongshuNoteVideo] = None
    class Config:
        orm_mode = True

class FavoriteItem(FavoriteItemBase):
    id: int
    created_at: datetime
    author: Optional[Author] = None
    collection: Optional[Collection] = None
    tags: List[Tag] = []
    bilibili_video_details: Optional[BilibiliVideoDetail] = None
    xiaohongshu_note_details: Optional[XiaohongshuNoteDetail] = None
    results: List[Result] = []

    class Config:
        orm_mode = True

class FavoriteItemBrief(BaseModel):
    """A lean version of FavoriteItem for list views like the dashboard pending queue."""
    id: int
    platform_item_id: str
    platform: PlatformEnum
    item_type: ItemTypeEnum
    title: str
    cover_url: Optional[str] = None
    status: FavoriteItemStatus
    favorited_at: datetime

    class Config:
        orm_mode = True

# Schema for paginated response
class PaginatedFavoriteItem(BaseModel):
    total: int
    items: List[FavoriteItem]


class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    result: Optional[Result] = None
    
    class Config:
        orm_mode = True
