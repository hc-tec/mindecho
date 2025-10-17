"""
This service layer contains the business logic for handling, processing,
and syncing favorite items from various platforms into the database.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sql_delete

from app.core.config import settings
from app.crud import crud_favorites
from app.db import models
from app.schemas import unified as schemas
from app.core.logging_config import get_logger
from dataclasses import asdict
from client_sdk.rpc_client_async import EAIRPCClient
from client_sdk.params import TaskParams, ServiceParams
from fastapi.encoders import jsonable_encoder

logger = get_logger(__name__)

# --- External Data Structures ---
# Note: These dataclasses are based on the user's data fetching scripts.
# They should be imported from the actual data source modules when integrated.


# --- Fully fleshed out dataclasses based on user feedback ---
@dataclass
class AuthorInfo:
    user_id: str
    username: str
    avatar: str
    xsec_token: Optional[str] = None
    gender: Optional[str] = None
    is_following: Optional[bool] = None
    is_followed: Optional[bool] = None
    user_type: Optional[str] = None


@dataclass
class CollectionItem:
    id: str
    title: str
    cover: Optional[str]
    description: Optional[str]
    item_count: int
    creator: AuthorInfo


@dataclass
class FavoriteVideoItem:
    collection_id: str
    fav_time: str

@dataclass
class VideoStatistic:
    view: int
    danmaku: int
    reply: int
    favorite: int
    coin: int
    share: int
    like: int

@dataclass
class VideoDimension:
    width: int
    height: int
    rotate: int

@dataclass
class VideoUrl:
    id: str
    base_url: str
    backup_url: str
    bandwidth: int
    mime_type: str
    codecs: str
    width: int
    height: int
    frame_rate: str

@dataclass
class AudioUrl:
    id: str
    base_url: str
    backup_url: str
    bandwidth: int
    mime_type: str
    codecs: str

@dataclass
class VideoSubtitleItem:
    content: str
    from_: float
    to: float
    sid: int
    location: int

@dataclass
class VideoSubtitleList:
    subtitles: List[VideoSubtitleItem]
    lang: str

@dataclass
class BiliVideoDetails:
    id: str
    bvid: str
    cover: str
    ctime: str
    pubdate: str
    duration_sec: int
    intro: str
    title: str
    creator: AuthorInfo
    tname: str
    tname_v2: str
    stat: VideoStatistic
    tags: List[str]
    video_url: Optional[VideoUrl]
    audio_url: Optional[AudioUrl]
    dimension: VideoDimension
    subtitles: Optional[VideoSubtitleList] = None # Added for convenience

@dataclass
class FavoriteVideoItem:
    collection_id: str
    fav_time: str

@dataclass
class BilibiliVideoBrief:
    bvid: str
    collection_id: str
    cover: str
    title: str
    intro: str
    creator: AuthorInfo
    fav_time: str
    # Platform-provided favorite record id; if present, we will use it as DB primary key
    favorite_id: str
    pubdate: Optional[str] = None  # Video publish timestamp


# ============================================================================
# Xiaohongshu Data Structures
# ============================================================================

@dataclass
class NoteStatistics:
    """Statistics for Xiaohongshu note."""
    like_count: int
    collect_count: int
    comment_count: int
    share_count: int


@dataclass
class VideoInfo:
    """Video information for Xiaohongshu note."""
    video_url: Optional[str] = None
    duration: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_url: Optional[str] = None


@dataclass
class XiaohongshuNoteBrief:
    """Brief information for Xiaohongshu note (from collection list)."""
    note_id: str
    xsec_token: str
    title: str
    author_info: AuthorInfo
    statistic: NoteStatistics
    cover_image: str
    collection_id: Optional[str] = None
    fav_time: Optional[str] = None


@dataclass
class XiaohongshuNoteDetails:
    """Detailed information for Xiaohongshu note."""
    note_id: str
    xsec_token: str
    title: str
    desc: str
    author_info: AuthorInfo
    tags: List[str]
    statistic: NoteStatistics
    published_date: Optional[str] = None  # Can be timestamp string or ISO date string
    ip_location: str = ""
    comment_num: str = "0"
    images: Optional[List[str]] = None
    video: Optional[VideoInfo] = None
    timestamp: Optional[str] = None


# This function remains as a low-level utility
async def _sync_single_bilibili_collection(db: AsyncSession, *, collection_data: CollectionItem) -> models.Collection:
    """
    Syncs a Bilibili collection to the database.
    Checks for existence before creation. Returns an instance with author loaded.
    """
    db_collection = await crud_favorites.collection.get_by_platform_id(
        db, platform="bilibili", platform_collection_id=collection_data.id
    )
    if db_collection:
        return db_collection

    creator_info = collection_data.creator
    db_author = await crud_favorites.author.get_by_platform_id(
        db, platform="bilibili", platform_user_id=creator_info.user_id
    )
    if not db_author:
        author_in = schemas.AuthorCreate(
            platform_user_id=creator_info.user_id,
            platform="bilibili",
            username=creator_info.username,
            avatar_url=creator_info.avatar,
        )
        db_author = await crud_favorites.author.create(db, obj_in=author_in)

    collection_in = schemas.CollectionCreate(
        platform_collection_id=collection_data.id,
        platform="bilibili",
        title=collection_data.title,
        description=collection_data.description,
        cover_url=collection_data.cover,
        item_count=collection_data.item_count,
    )
    
    # Exclude author_id from the dict to prevent passing it twice
    collection_dict = collection_in.dict(exclude={'author_id'})
    db_collection = models.Collection(**collection_dict, author_id=db_author.id)
    
    db.add(db_collection)
    await db.commit()
    await db.refresh(db_collection)
    return db_collection


async def _sync_single_bilibili_video_brief(db: AsyncSession, *, video_brief: BilibiliVideoBrief) -> models.FavoriteItem:
    """
    Syncs a Bilibili video with brief info. Creates a FavoriteItem entry
    without detailed stats. Idempotent.
    """
    # First, check if the item already exists to avoid race conditions and unnecessary work
    db_item = await crud_favorites.favorite_item.get_by_platform_item_id(db, platform_item_id=video_brief.bvid)
    if db_item:
        # If it exists, we can just return the full object
        return db_item

    # If it doesn't exist, proceed with creation
    author_info = video_brief.creator
    db_author = await crud_favorites.author.get_by_platform_id(
        db, platform="bilibili", platform_user_id=author_info.user_id
    )
    if not db_author:
        author_in = schemas.AuthorCreate(
            platform_user_id=author_info.user_id, platform="bilibili",
            username=author_info.username, avatar_url=author_info.avatar,
        )
        db_author = await crud_favorites.author.create(db, obj_in=author_in)

    db_collection = await crud_favorites.collection.get_by_platform_id(
        db, platform="bilibili", platform_collection_id=video_brief.collection_id
    )

    # Parse published_at if available
    published_at = None
    if video_brief.pubdate:
        try:
            published_at = datetime.fromtimestamp(int(video_brief.pubdate))
        except (ValueError, TypeError):
            pass
    
    item_in = schemas.FavoriteItemCreate(
        platform_item_id=video_brief.bvid,
        platform="bilibili",
        item_type="video",
        title=video_brief.title,
        intro=video_brief.intro,
        cover_url=video_brief.cover,
        favorited_at=datetime.fromtimestamp(int(video_brief.fav_time)),
        published_at=published_at,
    )
    item_dict = item_in.dict()
    db_item = models.FavoriteItem(
        **item_dict,
        author_id=db_author.id,
        platform_favorite_id=video_brief.favorite_id,
        collection_id=video_brief.collection_id,  # Platform collection ID (foreign key to collections.platform_collection_id)
    )
    
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item) # Refresh to get the ID from the database

    # After creation, fetch it again with all relations loaded to ensure a consistent return object
    refetched_item = await crud_favorites.favorite_item.get_full(db, id=db_item.id)
    return refetched_item


async def _update_single_bilibili_video_details(db: AsyncSession, *, video_details: BiliVideoDetails) -> models.FavoriteItem:
    """
    Updates an existing FavoriteItem with detailed information, including nested media details.
    """
    db_item = await crud_favorites.favorite_item.get_by_platform_item_id(db, platform_item_id=video_details.bvid)
    if not db_item:
        raise ValueError(f"FavoriteItem with bvid {video_details.bvid} not found. Sync brief info first.")

    # Update basic info that might change
    db_item.title = video_details.title
    db_item.intro = video_details.intro
    db_item.cover_url = video_details.cover
    # Safely parse and update published_at; some videos may have missing or non-numeric pubdate values
    try:
        if video_details.pubdate not in (None, "", "None"):
            db_item.published_at = datetime.fromtimestamp(int(video_details.pubdate))
    except (ValueError, TypeError, OSError):
        # Invalid timestamp, skip updating to preserve existing value
        pass

    # Update tags
    db_tags = await crud_favorites.tag.get_or_create_many(db, tag_names=video_details.tags)
    db_item.tags.clear()
    db_item.tags.extend(db_tags)

    # Create or Update BiliVideoDetail
    detail_model = db_item.bilibili_video_details
    if not detail_model:
        detail_model = models.BilibiliVideoDetail(favorite_item_id=db_item.id)
        db.add(detail_model)
        await db.flush()  # CRITICAL: Flush to get detail_model.id before creating nested objects
    else:
        # Ensure all nested relationships are loaded to avoid unique constraint errors
        await db.refresh(detail_model, ['video_url', 'audio_url', 'subtitles'])
        
    # Update fields from BiliVideoDetails dataclass
    stat = video_details.stat
    dim = video_details.dimension
    detail_model.bvid=video_details.bvid; detail_model.duration_sec=video_details.duration_sec;
    detail_model.view_count=stat.view; detail_model.like_count=stat.like;
    detail_model.coin_count=stat.coin; detail_model.favorite_count=stat.favorite;
    detail_model.reply_count=stat.reply; detail_model.share_count=stat.share;
    detail_model.danmaku_count=stat.danmaku; detail_model.tname=video_details.tname;
    detail_model.tname_v2=video_details.tname_v2; detail_model.dimension_width=dim.width;
    detail_model.dimension_height=dim.height; detail_model.dimension_rotate=dim.rotate

    # Create or Update VideoUrl
    v_url = video_details.video_url
    if v_url:
        # Delete any existing video_url for this detail (using direct SQL to avoid lazy loading issues)
        await db.execute(
            sql_delete(models.BilibiliVideoUrl).where(models.BilibiliVideoUrl.video_detail_id == detail_model.id)
        )
        await db.flush()
        
        # Create new video_url
        new_video_url = models.BilibiliVideoUrl(
            platform_media_id=str(v_url.id),
            base_url=v_url.base_url,
            backup_url=str(v_url.backup_url),
            bandwidth=v_url.bandwidth,
            mime_type=v_url.mime_type,
            codecs=v_url.codecs,
            width=v_url.width,
            height=v_url.height,
            frame_rate=v_url.frame_rate,
            video_detail_id=detail_model.id
        )
        db.add(new_video_url)

    # Create or Update AudioUrl
    a_url = video_details.audio_url
    if a_url:
        # Delete any existing audio_url for this detail (using direct SQL to avoid lazy loading issues)
        await db.execute(
            sql_delete(models.BilibiliAudioUrl).where(models.BilibiliAudioUrl.video_detail_id == detail_model.id)
        )
        await db.flush()
        
        # Create new audio_url
        new_audio_url = models.BilibiliAudioUrl(
            platform_media_id=str(a_url.id),
            base_url=a_url.base_url,
            backup_url=str(a_url.backup_url),
            bandwidth=a_url.bandwidth,
            mime_type=a_url.mime_type,
            codecs=a_url.codecs,
            video_detail_id=detail_model.id
        )
        db.add(new_audio_url)
        
    # Create/Update Subtitles
    if video_details.subtitles and video_details.subtitles.subtitles:
        # Clear existing subtitles using SQL DELETE (avoid lazy loading in async context)
        await db.execute(
            sql_delete(models.BilibiliSubtitle).where(models.BilibiliSubtitle.video_detail_id == detail_model.id)
        )
        await db.flush()

        # Add new subtitles
        for sub_item in video_details.subtitles.subtitles:
            new_sub = models.BilibiliSubtitle(
                sid=sub_item.sid, 
                lang=video_details.subtitles.lang,
                content=sub_item.content, 
                from_sec=sub_item.from_, 
                to_sec=sub_item.to,
                video_detail_id=detail_model.id
            )
            db.add(new_sub)

    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


# --- Granular, API-callable Services ---

def _to_collection_schema(db_obj: models.Collection) -> schemas.Collection:
    """Convert ORM Collection to Pydantic schema (detach from session)."""
    return schemas.Collection.model_validate(db_obj, from_attributes=True)

async def _to_favorite_schema_async(db: AsyncSession, db_obj: models.FavoriteItem) -> schemas.FavoriteItem:
    full_obj = await crud_favorites.favorite_item.get_by_platform_item_id_with_details(db, platform_item_id=db_obj.platform_item_id)
    return schemas.FavoriteItem.model_validate(full_obj, from_attributes=True)

async def sync_bilibili_collections_list(db: AsyncSession, *, max_collections: Optional[int] = None) -> List[schemas.Collection]:
    """
    API Service: Fetches and syncs the list of all Bilibili collections.
    """
    client = EAIRPCClient(base_url="http://127.0.0.1:8008", api_key="testkey")
    collections_synced = []
    try:
        await client.start()
        service_params = ServiceParams(need_raw_data=True, max_items=max_collections)
        results = await client.get_collection_list_from_bilibili(
            task_params=TaskParams(cookie_ids=settings.BILIBILI_COOKIE_IDS, close_page_when_task_finished=settings.BILIBILI_CLOSE_PAGE_WHEN_TASK_FINISHED),
            service_params=service_params,
        )
        # await client.stop()
        if not results.get("success"):
            raise RuntimeError(f"Failed to fetch collection list: {results.get('error')}")

        for collection_raw in results.get("data", []):
            creator_raw = collection_raw.get("creator", {})
            collection_item = CollectionItem(
                id=str(collection_raw.get("id")), title=collection_raw.get("title"),
                cover=collection_raw.get("cover"), description=collection_raw.get("description"),
                item_count=collection_raw.get("item_count", 0),
                creator=AuthorInfo(
                    user_id=str(creator_raw.get("user_id")), username=creator_raw.get("username"),
                    avatar=creator_raw.get("avatar")
                )
            )
            db_collection = await _sync_single_bilibili_collection(db, collection_data=collection_item)
            collections_synced.append(db_collection)
    except Exception as e:
        logger.error(e, exc_info=e)
    finally:
        await client.stop()
    # detach: convert to schemas
    return [_to_collection_schema(c) for c in collections_synced]


async def sync_videos_in_bilibili_collection(db: AsyncSession, *, platform_collection_id: str, max_videos: Optional[int] = None) -> List[schemas.FavoriteItem]:
    """
    API Service: Fetches and syncs brief video info for a specific collection.
    """
    db_collection = await crud_favorites.collection.get_by_platform_id(db, platform="bilibili", platform_collection_id=platform_collection_id)
    if not db_collection:
        raise ValueError(f"Collection with platform_id {platform_collection_id} not found.")
    if not db_collection.author:
        raise ValueError(f"Collection {platform_collection_id} is missing author information.")

    client = EAIRPCClient(base_url=settings.EAI_BASE_URL, api_key=settings.EAI_API_KEY)
    videos_synced = []
    try:
        await client.start()
        service_params = ServiceParams(need_raw_data=True, max_items=max_videos)
        results = await client.get_collection_list_videos_from_bilibili(
            collection_id=platform_collection_id,
            user_id=db_collection.author.platform_user_id,
            task_params=TaskParams(cookie_ids=settings.BILIBILI_COOKIE_IDS,
                                   close_page_when_task_finished=settings.BILIBILI_CLOSE_PAGE_WHEN_TASK_FINISHED),
            service_params=service_params, rpc_timeout_sec=120
        )
        if not results.get("success"):
            raise RuntimeError(f"Failed to fetch videos for collection {platform_collection_id}: {results.get('error')}")
        # Accept both shapes:
        # 1) { success: True, data: [ {..video..}, ... ] }
        # 2) { success: True, data: { data: [ {..video..}, ... ] } }
        raw_data = results.get("data")
        if isinstance(raw_data, list):
            video_list = raw_data
        elif isinstance(raw_data, dict):
            video_list = (raw_data.get("data") or []) if isinstance(raw_data.get("data"), list) else []
        else:
            video_list = []

        for video_raw in video_list:
            creator_raw = video_raw.get("creator", {})
            
            # Extract pubdate if available
            pubdate_raw = video_raw.get("pubdate")
            pubdate_str = str(pubdate_raw) if pubdate_raw is not None else None
            
            video_brief = BilibiliVideoBrief(
                bvid=video_raw.get("bvid"), 
                collection_id=platform_collection_id,
                cover=video_raw.get("cover"), 
                title=video_raw.get("title"),
                intro=video_raw.get("intro"), 
                fav_time=str(video_raw.get("fav_time")),
                creator=AuthorInfo(
                    user_id=str(creator_raw.get("user_id")), 
                    username=creator_raw.get("username"),
                    avatar=creator_raw.get("avatar")
                ),
                favorite_id=video_raw.get("id"),
                pubdate=pubdate_str,
            )
            db_item = await _sync_single_bilibili_video_brief(db, video_brief=video_brief)
            videos_synced.append(db_item)
    except Exception as e:
        logger.error(e, exc_info=e)
    finally:
        await client.stop()
    return [await _to_favorite_schema_async(db, v) for v in videos_synced]


async def sync_bilibili_videos_details(db: AsyncSession, *, bvids: List[str]) -> List[schemas.FavoriteItem]:
    """
    API Service: Fetches and syncs detailed info for a list of bvids.
    """
    client = EAIRPCClient(base_url=settings.EAI_BASE_URL, api_key=settings.EAI_API_KEY)
    videos_updated = []
    try:
        await client.start()
        for bvid in bvids:
            db_item = await crud_favorites.favorite_item.get_by_platform_item_id(db, platform_item_id=bvid)
            if not db_item:
                print(f"Warning: Skipping details for bvid {bvid} as it's not in DB. Sync it from its collection first.")
                continue

            results = await client.get_video_details_from_bilibili(
                bvid=bvid,
                task_params=TaskParams(cookie_ids=settings.BILIBILI_COOKIE_IDS,
                                       close_page_when_task_finished=settings.BILIBILI_CLOSE_PAGE_WHEN_TASK_FINISHED),
                service_params=ServiceParams(need_raw_data=True),
            )
            if not results.get("success"):
                print(f"Warning: Failed to fetch details for video {bvid}: {results.get('error')}")
                continue
            
            # Accept both shapes: { data: { ...details... } } or { data: { details: { data: {...} } } }
            outer_data = results.get("data", {}) or {}
            if isinstance(outer_data.get("details"), dict):
                details_data = outer_data["details"].get("data", {}) or {}
            else:
                # When RPC returns the details directly under 'data' without nesting
                details_data = outer_data
            if not details_data:
                print(f"Warning: 'details' key missing or empty in response for bvid {bvid}. Raw response: {results}")
                continue

            creator_data = details_data.get("creator", {}) or {}
            stat_data = details_data.get("stat", {}) or {}
            dim_data = details_data.get("dimension", {}) or {}
            v_url_data = details_data.get("video_url", {}) or {}
            a_url_data = details_data.get("audio_url", {}) or {}
            subs_outer = outer_data.get("subtitles", {}) or {}
            subs_data = subs_outer.get("data", {}) if subs_outer.get("success") else {}

            # --- Robust, field-by-field object construction ---
            video_url_obj = None
            if v_url_data:
                backup_urls = v_url_data.get("backup_url", []) or []
                video_url_obj = VideoUrl(
                    id=v_url_data.get("id"),
                    base_url=v_url_data.get("base_url"),
                    backup_url=backup_urls[0] if backup_urls else None,
                    bandwidth=v_url_data.get("bandwidth") or 0,
                    mime_type=v_url_data.get("mime_type"),
                    codecs=v_url_data.get("codecs"),
                    width=v_url_data.get("width") or 0,
                    height=v_url_data.get("height") or 0,
                    frame_rate=v_url_data.get("frame_rate"),
                )

            audio_url_obj = None
            if a_url_data:
                backup_urls = a_url_data.get("backup_url", []) or []
                audio_url_obj = AudioUrl(
                    id=a_url_data.get("id"),
                    base_url=a_url_data.get("base_url"),
                    backup_url=backup_urls[0] if backup_urls else None,
                    bandwidth=a_url_data.get("bandwidth") or 0,
                    mime_type=a_url_data.get("mime_type"),
                    codecs=a_url_data.get("codecs"),
                )
            
            subtitles_obj = None
            if subs_data and subs_data.get('subtitles'):
                subtitles_obj = VideoSubtitleList(
                    lang=subs_data.get('lang'),
                    subtitles=[
                        VideoSubtitleItem(
                            sid=s.get('sid'),
                            from_=s.get('from'),
                            to=s.get('to'),
                            content=s.get('content'),
                            location=s.get('location')
                        ) for s in subs_data.get('subtitles', [])
                    ]
                )
            
            # Build safe defaults for stats and dimension
            stat_obj = VideoStatistic(
                view=stat_data.get("view") or 0,
                danmaku=stat_data.get("danmaku") or 0,
                reply=stat_data.get("reply") or 0,
                favorite=stat_data.get("favorite") or 0,
                coin=stat_data.get("coin") or 0,
                share=stat_data.get("share") or 0,
                like=stat_data.get("like") or 0,
            )
            
            dim_obj = VideoDimension(
                width=dim_data.get("width") or 0,
                height=dim_data.get("height") or 0,
                rotate=dim_data.get("rotate") or 0,
            )

            # Normalize tags to list[str]
            raw_tags = details_data.get("tags") or []
            norm_tags: list[str] = []
            for t in raw_tags:
                if isinstance(t, str):
                    norm_tags.append(t)
                elif isinstance(t, dict):
                    name = t.get("tag_name") or t.get("name") or t.get("title")
                    if name:
                        norm_tags.append(str(name))

            # Assemble the final, complete BiliVideoDetails object
            video_details = BiliVideoDetails(
                id=details_data.get("id"),
                bvid=details_data.get("bvid") or bvid,
                cover=details_data.get("cover"),
                pubdate=str(details_data.get("pubdate") or ""),
                duration_sec=details_data.get("duration_sec") or 0,
                intro=details_data.get("intro") or "",
                title=details_data.get("title") or "",
                creator=AuthorInfo(
                    user_id=str(creator_data.get("user_id")) if creator_data.get("user_id") is not None else "",
                    username=creator_data.get("username") or "",
                    avatar=creator_data.get("avatar") or "",
                ),
                tags=[tag for tag in details_data.get("tags", [])],
                stat=stat_obj,
                tname=details_data.get("tname"),
                tname_v2=details_data.get("tname_v2"),
                dimension=dim_obj,
                video_url=video_url_obj,
                audio_url=audio_url_obj,
                subtitles=subtitles_obj,
                ctime=details_data.get("ctime"),
            )
            updated_item = await _update_single_bilibili_video_details(db, video_details=video_details)
            videos_updated.append(updated_item)
    except Exception as e:
        logger.error(e, exc_info=e)
    finally:
        await client.stop()
    return [await _to_favorite_schema_async(db, v) for v in videos_updated]


async def ingest_bilibili_video_briefs(db: AsyncSession, *, items: List[Dict]) -> List[models.FavoriteItem]:
    """Ingest a list of Bilibili video brief dicts from plugin stream events.

    Each item is expected to include fields: bvid, collection_id, cover, title, intro,
    creator { user_id, username, avatar }, fav_time.
    If the favorite item already exists, it will be returned as-is.
    """
    ingested: List[models.FavoriteItem] = []
    for raw in items or []:
        try:
            creator_raw = (raw or {}).get("creator") or {}
            
            # Extract pubdate if available
            pubdate_raw = (raw or {}).get("pubdate")
            pubdate_str = str(pubdate_raw) if pubdate_raw is not None else None
            
            # Extract favorite_id
            favorite_id_raw = (raw or {}).get("id")
            favorite_id = str(favorite_id_raw) if favorite_id_raw is not None else None
            
            brief = BilibiliVideoBrief(
                bvid=str((raw or {}).get("bvid")),
                collection_id=str((raw or {}).get("collection_id")),
                cover=(raw or {}).get("cover"),
                title=(raw or {}).get("title") or "",
                intro=(raw or {}).get("intro") or "",
                creator=AuthorInfo(
                    user_id=str(creator_raw.get("user_id")) if creator_raw.get("user_id") is not None else "",
                    username=creator_raw.get("username") or "",
                    avatar=creator_raw.get("avatar") or "",
                ),
                fav_time=str((raw or {}).get("fav_time") or "0"),
                favorite_id=favorite_id,
                pubdate=pubdate_str,
            )
            db_item = await _sync_single_bilibili_video_brief(db, video_brief=brief)
            ingested.append(db_item)
        except Exception as e:
            logger.exception("Failed to ingest video brief from plugin event: %s", raw)
    return ingested


# ============================================================================
# Xiaohongshu Sync Functions
# ============================================================================

async def _sync_single_xiaohongshu_note_brief(db: AsyncSession, *, note_brief: XiaohongshuNoteBrief) -> models.FavoriteItem:
    """
    Syncs a Xiaohongshu note with brief info. Creates a FavoriteItem entry
    without detailed information. Idempotent.
    """
    # Check if the item already exists
    db_item = await crud_favorites.favorite_item.get_by_platform_item_id(db, platform_item_id=note_brief.note_id)
    if db_item:
        return db_item

    # Ensure author exists
    author_info = note_brief.author_info
    db_author = await crud_favorites.author.get_by_platform_id(
        db, platform="xiaohongshu", platform_user_id=author_info.user_id
    )
    if not db_author:
        author_in = schemas.AuthorCreate(
            platform_user_id=author_info.user_id,
            platform="xiaohongshu",
            username=author_info.username,
            avatar_url=author_info.avatar,
        )
        db_author = await crud_favorites.author.create(db, obj_in=author_in)

    # Find collection if specified
    db_collection = None
    if note_brief.collection_id:
        db_collection = await crud_favorites.collection.get_by_platform_id(
            db, platform="xiaohongshu", platform_collection_id=note_brief.collection_id
        )

    # Parse favorited_at
    favorited_at = datetime.utcnow()
    if note_brief.fav_time:
        try:
            favorited_at = datetime.fromtimestamp(int(note_brief.fav_time))
        except (ValueError, TypeError):
            pass

    # Create FavoriteItem
    item_in = schemas.FavoriteItemCreate(
        platform_item_id=note_brief.note_id,
        platform="xiaohongshu",
        item_type="note",
        title=note_brief.title,
        intro="",  # Brief doesn't have description
        cover_url=note_brief.cover_image,
        favorited_at=favorited_at,
        published_at=None,  # Will be filled in details
    )

    item_dict = item_in.dict()
    db_item = models.FavoriteItem(
        **item_dict,
        author_id=db_author.id,
        collection_id=note_brief.collection_id if note_brief.collection_id else None,
    )

    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)

    # Fetch with all relations loaded
    refetched_item = await crud_favorites.favorite_item.get_full(db, id=db_item.id)
    return refetched_item


async def _update_single_xiaohongshu_note_details(db: AsyncSession, *, note_details: XiaohongshuNoteDetails) -> models.FavoriteItem:
    """
    Updates an existing FavoriteItem with detailed information for Xiaohongshu note.
    """
    db_item = await crud_favorites.favorite_item.get_by_platform_item_id(db, platform_item_id=note_details.note_id)
    if not db_item:
        raise ValueError(f"FavoriteItem with note_id {note_details.note_id} not found. Sync brief info first.")

    # Update basic info
    db_item.title = note_details.title
    db_item.intro = note_details.desc

    # Try to parse published_date - can be int timestamp or ISO string
    try:
        if note_details.published_date:
            # Try parsing as integer timestamp first
            try:
                db_item.published_at = datetime.fromtimestamp(int(note_details.published_date))
            except (ValueError, TypeError):
                # If that fails, try parsing as ISO format string
                if isinstance(note_details.published_date, str):
                    db_item.published_at = datetime.fromisoformat(note_details.published_date.replace('Z', '+00:00'))
    except (ValueError, TypeError, OSError):
        # Invalid timestamp, skip updating to preserve existing value
        pass

    # Update tags
    db_tags = await crud_favorites.tag.get_or_create_many(db, tag_names=note_details.tags)
    db_item.tags.clear()
    db_item.tags.extend(db_tags)

    # Create or Update XiaohongshuNoteDetail
    detail_model = db_item.xiaohongshu_note_details
    if not detail_model:
        detail_model = models.XiaohongshuNoteDetail(favorite_item_id=db_item.id)
        db.add(detail_model)
        await db.flush()  # Get detail_model.id before creating nested objects
    else:
        # Ensure nested relationships are loaded
        await db.refresh(detail_model, ['images', 'video'])

    # Update detail fields
    detail_model.note_id = note_details.note_id
    detail_model.xsec_token = note_details.xsec_token
    detail_model.desc = note_details.desc
    detail_model.ip_location = note_details.ip_location
    detail_model.published_date = note_details.published_date
    detail_model.like_count = note_details.statistic.like_count
    detail_model.collect_count = note_details.statistic.collect_count
    detail_model.comment_count = note_details.statistic.comment_count
    detail_model.share_count = note_details.statistic.share_count
    detail_model.fetched_timestamp = note_details.timestamp

    # Handle images
    if note_details.images:
        # Delete existing images
        await db.execute(
            sql_delete(models.XiaohongshuNoteImage).where(
                models.XiaohongshuNoteImage.note_detail_id == detail_model.id
            )
        )
        await db.flush()

        # Add new images
        for idx, image_url in enumerate(note_details.images):
            new_image = models.XiaohongshuNoteImage(
                image_url=image_url,
                order_index=idx,
                note_detail_id=detail_model.id
            )
            db.add(new_image)

    # Handle video
    if note_details.video:
        # Delete existing video
        await db.execute(
            sql_delete(models.XiaohongshuNoteVideo).where(
                models.XiaohongshuNoteVideo.note_detail_id == detail_model.id
            )
        )
        await db.flush()

        # Create new video
        new_video = models.XiaohongshuNoteVideo(
            video_url=note_details.video.video_url,
            duration=note_details.video.duration,
            width=note_details.video.width,
            height=note_details.video.height,
            thumbnail_url=note_details.video.thumbnail_url,
            note_detail_id=detail_model.id
        )
        db.add(new_video)

    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


async def sync_xiaohongshu_collections_list(db: AsyncSession, *, max_collections: Optional[int] = None) -> List[schemas.Collection]:
    """
    API Service: Fetches and syncs the list of all Xiaohongshu collections.
    """
    from app.core.config import settings

    client = EAIRPCClient(base_url=settings.EAI_BASE_URL, api_key=settings.EAI_API_KEY)
    collections_synced = []
    try:
        await client.start()
        service_params = ServiceParams(need_raw_data=True, max_items=max_collections)
        results = await client.get_collection_list_from_xiaohongshu(
            task_params=TaskParams(
                cookie_ids=getattr(settings, 'XIAOHONGSHU_COOKIE_IDS', []),
                close_page_when_task_finished=True
            ),
            service_params=service_params,
        )

        if not results.get("success"):
            raise RuntimeError(f"Failed to fetch Xiaohongshu collection list: {results.get('error')}")

        for collection_raw in results.get("data", []):
            creator_raw = collection_raw.get("creator", {})
            collection_item = CollectionItem(
                id=str(collection_raw.get("id")),
                title=collection_raw.get("title"),
                cover=collection_raw.get("cover"),
                description=collection_raw.get("description"),
                item_count=collection_raw.get("item_count", 0),
                creator=AuthorInfo(
                    user_id=str(creator_raw.get("user_id")),
                    username=creator_raw.get("username"),
                    avatar=creator_raw.get("avatar")
                )
            )

            # Sync using generic collection sync (platform-agnostic)
            db_collection = await crud_favorites.collection.get_by_platform_id(
                db, platform="xiaohongshu", platform_collection_id=collection_item.id
            )
            if not db_collection:
                # Create author first
                db_author = await crud_favorites.author.get_by_platform_id(
                    db, platform="xiaohongshu", platform_user_id=creator_raw.get("user_id")
                )
                if not db_author:
                    author_in = schemas.AuthorCreate(
                        platform_user_id=str(creator_raw.get("user_id")),
                        platform="xiaohongshu",
                        username=creator_raw.get("username"),
                        avatar_url=creator_raw.get("avatar"),
                    )
                    db_author = await crud_favorites.author.create(db, obj_in=author_in)

                # Create collection
                collection_in = schemas.CollectionCreate(
                    platform_collection_id=collection_item.id,
                    platform="xiaohongshu",
                    title=collection_item.title,
                    description=collection_item.description,
                    cover_url=collection_item.cover,
                    item_count=collection_item.item_count,
                )
                collection_dict = collection_in.dict(exclude={'author_id'})
                db_collection = models.Collection(**collection_dict, author_id=db_author.id)
                db.add(db_collection)
                await db.commit()
                await db.refresh(db_collection)

            collections_synced.append(db_collection)
    except Exception as e:
        logger.error(f"Failed to sync Xiaohongshu collections: {e}", exc_info=True)
    finally:
        await client.stop()

    return [_to_collection_schema(c) for c in collections_synced]


async def sync_notes_in_xiaohongshu_collection(db: AsyncSession, *, platform_collection_id: str, max_notes: Optional[int] = None) -> List[schemas.FavoriteItem]:
    """
    API Service: Fetches and syncs brief note info for a specific Xiaohongshu collection.
    """
    from app.core.config import settings

    db_collection = await crud_favorites.collection.get_by_platform_id(
        db, platform="xiaohongshu", platform_collection_id=platform_collection_id
    )
    if not db_collection:
        raise ValueError(f"Collection with platform_id {platform_collection_id} not found.")

    client = EAIRPCClient(base_url=settings.EAI_BASE_URL, api_key=settings.EAI_API_KEY)
    notes_synced = []
    try:
        await client.start()
        service_params = ServiceParams(need_raw_data=True, max_items=max_notes)
        results = await client.get_collection_favorite_items_from_xiaohongshu(
            task_params=TaskParams(
                cookie_ids=getattr(settings, 'XIAOHONGSHU_COOKIE_IDS', []),
                close_page_when_task_finished=True
            ),
            service_params=service_params,
            collection_id=platform_collection_id,
        )

        if not results.get("success"):
            raise RuntimeError(f"Failed to fetch notes for collection {platform_collection_id}: {results.get('error')}")

        raw_data = results.get("data", [])
        if isinstance(raw_data, dict):
            note_list = raw_data.get("data", [])
        else:
            note_list = raw_data

        for note_raw in note_list:
            author_raw = note_raw.get("author_info", {})
            stat_raw = note_raw.get("statistic", {})

            note_brief = XiaohongshuNoteBrief(
                note_id=str(note_raw.get("id")),
                xsec_token=note_raw.get("xsec_token", ""),
                title=note_raw.get("title", ""),
                author_info=AuthorInfo(
                    user_id=str(author_raw.get("user_id")),
                    username=author_raw.get("username", ""),
                    avatar=author_raw.get("avatar", "")
                ),
                statistic=NoteStatistics(
                    like_count=stat_raw.get("like_count", 0),
                    collect_count=stat_raw.get("collect_count", 0),
                    comment_count=stat_raw.get("comment_count", 0),
                    share_count=stat_raw.get("share_count", 0),
                ),
                cover_image=note_raw.get("cover_image", ""),
                collection_id=platform_collection_id,
                fav_time=str(note_raw.get("fav_time", "")),
            )

            db_item = await _sync_single_xiaohongshu_note_brief(db, note_brief=note_brief)
            notes_synced.append(db_item)
    except Exception as e:
        logger.error(f"Failed to sync Xiaohongshu notes: {e}", exc_info=True)
    finally:
        await client.stop()

    return [await _to_favorite_schema_async(db, n) for n in notes_synced]


async def sync_xiaohongshu_note_details_single(
    db: AsyncSession,
    *,
    note_id: str,
    xsec_token: str,
    max_retry_attempts: int = 5
) -> Optional[models.FavoriteItem]:
    """
    Fetch details for a single Xiaohongshu note with retry support.

    Args:
        db: Database session
        note_id: Note ID
        xsec_token: Note's xsec_token
        max_retry_attempts: Maximum number of retry attempts (default: 5)

    Returns:
        Updated FavoriteItem or None if failed
    """
    from app.core.config import settings

    db_item = await crud_favorites.favorite_item.get_by_platform_item_id(db, platform_item_id=note_id)
    if not db_item:
        logger.warning(f"Note {note_id} not found in DB")
        return None

    # Check if we've exceeded retry attempts
    if db_item.details_fetch_attempts >= max_retry_attempts:
        logger.warning(f"Note {note_id} has exceeded max retry attempts ({max_retry_attempts})")
        return None

    client = EAIRPCClient(base_url=settings.EAI_BASE_URL, api_key=settings.EAI_API_KEY)
    try:
        await client.start()

        # Update attempt counter
        db_item.details_fetch_attempts = (db_item.details_fetch_attempts or 0) + 1
        db_item.details_last_attempt_at = datetime.utcnow()
        await db.commit()

        # Fetch details from Xiaohongshu
        results = await client.get_note_details_from_xiaohongshu(
            note_id=note_id,
            xsec_token=xsec_token,
            wait_time_sec=3,
            task_params=TaskParams(
                cookie_ids=settings.XIAOHONGSHU_COOKIE_IDS,
                close_page_when_task_finished=True
            ),
            service_params=ServiceParams(need_raw_data=True),
            rpc_timeout_sec=120
        )

        if not results.get("success"):
            error_msg = results.get("error", "Unknown error")
            logger.warning(f"Failed to fetch details for note {note_id}: {error_msg}")
            db_item.details_fetch_error = error_msg
            await db.commit()
            return None

        details_data = results.get("data", {})
        if not details_data:
            logger.warning(f"Empty details data for note {note_id}")
            db_item.details_fetch_error = "Empty response data"
            await db.commit()
            return None

        # Parse response data
        author_raw = details_data.get("author_info", {})
        stat_raw = details_data.get("statistic", {})
        video_raw = details_data.get("video")

        video_info = None
        if video_raw:
            video_info = VideoInfo(
                video_url=video_raw.get("src"),  # Use 'src' according to API format
                duration=video_raw.get("duration_sec"),
                width=None,  # Not in the provided format
                height=None,
                thumbnail_url=None
            )

        # Handle published_date - convert to string if it's an integer
        published_date_raw = details_data.get("date")
        published_date = str(published_date_raw) if published_date_raw is not None else None

        note_details = XiaohongshuNoteDetails(
            note_id=str(details_data.get("id")),
            xsec_token=details_data.get("xsec_token", ""),
            title=details_data.get("title", ""),
            desc=details_data.get("desc", ""),
            author_info=AuthorInfo(
                user_id=str(author_raw.get("user_id")),
                username=author_raw.get("username", ""),
                avatar=author_raw.get("avatar", "")
            ),
            tags=details_data.get("tags", []),
            published_date=published_date,
            ip_location=details_data.get("ip_zh", ""),
            comment_num=details_data.get("comment_num", "0"),
            statistic=NoteStatistics(
                like_count=int(stat_raw.get("like_num", 0)) if stat_raw.get("like_num") else 0,
                collect_count=int(stat_raw.get("collect_num", 0)) if stat_raw.get("collect_num") else 0,
                comment_count=int(stat_raw.get("chat_num", 0)) if stat_raw.get("chat_num") else 0,
                share_count=0,  # Not in the provided format
            ),
            images=details_data.get("images", []),
            video=video_info,
            timestamp=details_data.get("timestamp"),
        )

        # Update database with details
        updated_item = await _update_single_xiaohongshu_note_details(db, note_details=note_details)

        # Clear error fields on success
        updated_item.details_fetch_error = None
        await db.commit()

        logger.info(f"Successfully fetched details for note {note_id}")
        return updated_item

    except Exception as e:
        logger.error(f"Exception fetching details for note {note_id}: {e}", exc_info=True)
        db_item.details_fetch_error = str(e)
        await db.commit()
        return None
    finally:
        await client.stop()


async def sync_xiaohongshu_notes_details(db: AsyncSession, *, note_ids: List[str]) -> List[schemas.FavoriteItem]:
    """
    API Service: Fetches and syncs detailed info for a list of Xiaohongshu note IDs.
    Uses the new single-note fetcher with retry support.
    """
    notes_updated = []

    for note_id in note_ids:
        db_item = await crud_favorites.favorite_item.get_by_platform_item_id(db, platform_item_id=note_id)
        if not db_item:
            logger.warning(f"Skipping details for note_id {note_id} as it's not in DB.")
            continue

        # Get xsec_token from db_item or xiaohongshu_note_details
        xsec_token = ""
        if hasattr(db_item, 'xiaohongshu_note_details') and db_item.xiaohongshu_note_details:
            xsec_token = db_item.xiaohongshu_note_details.xsec_token or ""

        updated_item = await sync_xiaohongshu_note_details_single(
            db,
            note_id=note_id,
            xsec_token=xsec_token
        )

        if updated_item:
            notes_updated.append(updated_item)

    return [await _to_favorite_schema_async(db, n) for n in notes_updated]