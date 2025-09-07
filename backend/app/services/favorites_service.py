"""
This service layer contains the business logic for handling, processing,
and syncing favorite items from various platforms into the database.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict

from sqlalchemy.ext.asyncio import AsyncSession

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

    item_in = schemas.FavoriteItemCreate(
        platform_item_id=video_brief.bvid,
        platform="bilibili",
        item_type="video",
        title=video_brief.title,
        intro=video_brief.intro,
        cover_url=video_brief.cover,
        favorited_at=datetime.fromtimestamp(int(video_brief.fav_time)),
    )
    item_dict = item_in.dict()
    db_item = models.FavoriteItem(
        **item_dict,
        author_id=db_author.id,
        collection_id=db_collection.id if db_collection else None,
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
    db_item.published_at = datetime.fromtimestamp(int(video_details.pubdate))

    # Update tags
    db_tags = await crud_favorites.tag.get_or_create_many(db, tag_names=video_details.tags)
    db_item.tags.clear()
    db_item.tags.extend(db_tags)

    # Create or Update BiliVideoDetail
    detail_model = db_item.bilibili_video_details
    if not detail_model:
        detail_model = models.BilibiliVideoDetail(favorite_item_id=db_item.id)
        db.add(detail_model)
        
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
        if not detail_model.video_url:
            detail_model.video_url = models.BilibiliVideoUrl()
        
        detail_model.video_url.platform_media_id=str(v_url.id)
        detail_model.video_url.base_url=v_url.base_url
        detail_model.video_url.backup_url=str(v_url.backup_url)
        detail_model.video_url.bandwidth=v_url.bandwidth
        detail_model.video_url.mime_type=v_url.mime_type; detail_model.video_url.codecs=v_url.codecs
        detail_model.video_url.width=v_url.width; detail_model.video_url.height=v_url.height
        detail_model.video_url.frame_rate=v_url.frame_rate

    # Create or Update AudioUrl
    a_url = video_details.audio_url
    if a_url:
        if not detail_model.audio_url:
            detail_model.audio_url = models.BilibiliAudioUrl()

        detail_model.audio_url.platform_media_id=str(a_url.id)
        detail_model.audio_url.base_url=a_url.base_url
        detail_model.audio_url.backup_url=str(a_url.backup_url)
        detail_model.audio_url.bandwidth=a_url.bandwidth
        detail_model.audio_url.mime_type=a_url.mime_type; detail_model.audio_url.codecs=a_url.codecs
        
    # Create/Update Subtitles
    if video_details.subtitles and video_details.subtitles.subtitles:
        # Clear existing subtitles before adding new ones
        await db.flush() # First, process other changes
        for sub in detail_model.subtitles: # Then, manually delete existing subtitles
            await db.delete(sub)
        await db.flush()

        for sub_item in video_details.subtitles.subtitles:
            new_sub = models.BilibiliSubtitle(
                sid=sub_item.sid, lang=video_details.subtitles.lang,
                content=sub_item.content, from_sec=sub_item.from_, to_sec=sub_item.to
            )
            detail_model.subtitles.append(new_sub)

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
            task_params=TaskParams(cookie_ids=["23d87982-a801-4d12-ae93-50a85e336e98"], close_page_when_task_finished=True),
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

    client = EAIRPCClient(base_url="http://127.0.0.1:8008", api_key="testkey")
    videos_synced = []
    try:
        await client.start()
        service_params = ServiceParams(need_raw_data=True, max_items=max_videos)
        results = await client.get_collection_list_videos_from_bilibili(
            collection_id=platform_collection_id,
            user_id=db_collection.author.platform_user_id,
            task_params=TaskParams(cookie_ids=["23d87982-a801-4d12-ae93-50a85e336e98"], close_page_when_task_finished=True),
            service_params=service_params, rpc_timeout_sec=120
        )
        if not results.get("success"):
            raise RuntimeError(f"Failed to fetch videos for collection {platform_collection_id}: {results.get('error')}")

        for video_raw in results.get("data", []):
            creator_raw = video_raw.get("creator", {})
            video_brief = BilibiliVideoBrief(
                bvid=video_raw.get("bvid"), collection_id=platform_collection_id,
                cover=video_raw.get("cover"), title=video_raw.get("title"),
                intro=video_raw.get("intro"), fav_time=str(video_raw.get("fav_time")),
                creator=AuthorInfo(
                    user_id=str(creator_raw.get("user_id")), username=creator_raw.get("username"),
                    avatar=creator_raw.get("avatar")
                )
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
    client = EAIRPCClient(base_url="http://127.0.0.1:8008", api_key="testkey")
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
                task_params=TaskParams(cookie_ids=["23d87982-a801-4d12-ae93-50a85e336e98"], close_page_when_task_finished=True),
                service_params=ServiceParams(need_raw_data=True),
            )
            if not results.get("success"):
                print(f"Warning: Failed to fetch details for video {bvid}: {results.get('error')}")
                continue
            
            # Accept both shapes: { data: { ...details... } } or { data: { details: { data: {...} } } }
            outer_data = results.get("data", {}) or {}
            details_data = outer_data.get("details", {}).get("data", {}) if isinstance(outer_data.get("details"), dict) else {}
            if not details_data:
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
            if subs_data and subs_data.get('body'):
                subtitles_obj = VideoSubtitleList(
                    lang=subs_data.get('lang'),
                    subtitles=[
                        VideoSubtitleItem(
                            sid=s.get('sid'),
                            from_=s.get('from'),
                            to=s.get('to'),
                            content=s.get('content')
                        ) for s in subs_data.get('body', [])
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
