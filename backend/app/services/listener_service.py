import asyncio
import datetime
import json
from typing import Any, Dict, Optional, List, Tuple

from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.runtime_config import runtime_config
from app.crud import crud_favorites, crud_tasks
from app.db import models
from app.db.base import AsyncSessionLocal
from app.db.models import FavoriteItem, Collection, Workshop as WorkshopModel, Task as TaskModel, TaskStatus
from app.schemas.unified import AuthorCreate, FavoriteItemCreate
from app.services import favorites_service
from app.services import workshop_service
from app.services.stream_manager import stream_manager


logger = get_logger(__name__)


async def _parse_executor_config(row: WorkshopModel) -> Optional[Dict[str, Any]]:
    """Safely parse executor_config JSON to a dict, or return None."""
    if not row.executor_config:
        return None
    try:
        return json.loads(row.executor_config)
    except Exception:
        logger.warning("Invalid executor_config JSON for workshop_id=%s", row.workshop_id)
        return None


async def _resolve_workshop_id_for_item(db, db_item: FavoriteItem, event: Dict[str, Any]) -> str:
    """Decide which workshop_id to use for a new favorite item.

    Preference:
    1) If the item's collection title equals some workshop.workshop_name AND that workshop has
       executor_config.listening_enabled == True, use that workshop.
    2) Otherwise, fallback to runtime category mapping.
    """
    # Default
    selected = "summary-01"

    try:
        collection: Optional[Collection] = None
        if db_item.collection_id:
            collection = await db.get(Collection, db_item.collection_id)

        # 1) Binding by collection_id has highest priority
        rows = (await db.execute(select(WorkshopModel))).scalars().all()
        for r in rows:
            cfg = await _parse_executor_config(r)
            if isinstance(cfg, dict) and cfg.get("listening_enabled") is True and cfg.get("binding_collection_id") == db_item.collection_id:
                return r.workshop_id

        # 2) Title match when enabled
        if collection and collection.title:
            row = (
                (await db.execute(select(WorkshopModel).where(WorkshopModel.name == collection.title)))
                .scalars()
                .first()
            )
            if row:
                cfg = await _parse_executor_config(row)
                if isinstance(cfg, dict) and cfg.get("listening_enabled") is True:
                    return row.workshop_id

        # Fallback to runtime-config category map
        category = (event.get("item") or {}).get("category") or event.get("category")
        mapping = runtime_config.get_category_map()
        selected = mapping.get(category or "", selected)
    except Exception:
        logger.exception("Failed to resolve workshop for item_id=%s", db_item.id)

    return selected


def _extract_items_from_event(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract raw brief items from plugin event.

    Prefers payload.result.data.added.data, falls back to payload.result.data.data.
    Returns a list of dicts (may be empty).
    """
    payload = event.get("payload") or {}
    result = payload.get("result") if isinstance(payload, dict) else None
    if not isinstance(result, dict) or not result.get("success"):
        return []
    data_block = result.get("data") or {}
    added_block = (data_block.get("added") or {}) if isinstance(data_block, dict) else {}
    items_added = (added_block.get("data") or []) if isinstance(added_block, dict) else []
    all_items = (data_block.get("data") or []) if isinstance(data_block, dict) else []
    return items_added if items_added else all_items


async def _ingest_brief_items(db, items: List[Dict[str, Any]]) -> List[FavoriteItem]:
    """Idempotently ingest brief items into DB using CRUD helpers.

    Ensures Author/Collection relationships exist, returns list of FavoriteItem rows.
    """
    ingested: List[FavoriteItem] = []
    for raw in items:
        try:
            bvid = str((raw or {}).get("bvid"))
            if not bvid:
                continue
            existing = await crud_favorites.favorite_item.get_by_platform_item_id(db, platform_item_id=bvid)
            if existing:
                ingested.append(existing)
                continue

            creator = (raw or {}).get("creator") or {}
            db_author = await crud_favorites.author.get_by_platform_id(
                db, platform=models.PlatformEnum.bilibili, platform_user_id=str(creator.get("user_id") or "")
            )
            if not db_author:
                db_author = await crud_favorites.author.create(
                    db,
                    obj_in=AuthorCreate(
                        platform_user_id=str(creator.get("user_id") or ""),
                        platform=models.PlatformEnum.bilibili,
                        username=str(creator.get("username") or ""),
                        avatar_url=str(creator.get("avatar") or ""),
                    ),
                )

            collection_platform_id = str((raw or {}).get("collection_id") or "")
            db_collection = None
            if collection_platform_id:
                db_collection = await crud_favorites.collection.get_by_platform_id(
                    db, platform=models.PlatformEnum.bilibili, platform_collection_id=collection_platform_id
                )

            item_in = FavoriteItemCreate(
                platform_item_id=bvid,
                platform=models.PlatformEnum.bilibili,
                item_type=models.ItemTypeEnum.video,
                title=str((raw or {}).get("title") or ""),
                intro=str((raw or {}).get("intro") or ""),
                cover_url=str((raw or {}).get("cover") or ""),
                favorited_at=datetime.datetime.fromtimestamp(int((raw or {}).get("fav_time") or 0)),
            )
            db_item = await crud_favorites.favorite_item.create_brief_with_relationships(
                db,
                item_in=item_in,
                author_id=db_author.id,
                collection_id=db_collection.id if db_collection else None,
            )
            ingested.append(db_item)
        except Exception:
            logger.exception("Failed to ingest brief item from stream")
    return ingested


async def _sync_details_for_items(db, items: List[FavoriteItem]) -> None:
    """Ensure details exist for the given brief items by calling the favorites sync service.

    This follows the requirement to call the favorite sync method to obtain details.
    """
    bvids = [fi.platform_item_id for fi in items if getattr(fi, "platform_item_id", None)]
    if not bvids:
        return
    await favorites_service.sync_bilibili_videos_details(db, bvids=bvids)


async def _create_tasks_for_items(db, items: List[FavoriteItem], event: Dict[str, Any]) -> None:
    """Create analysis tasks for items that already have details, skipping existing unfinished tasks."""
    for db_item in items:
        try:
            full = await crud_favorites.favorite_item.get_by_platform_item_id_with_details(
                db, platform_item_id=db_item.platform_item_id
            )
            if not getattr(full, "bilibili_video_details", None):
                continue

            existing_task = await crud_tasks.task.get_unfinished_task_for_item(db, favorite_item_id=db_item.id)
            if existing_task:
                continue

            workshop_id = await _resolve_workshop_id_for_item(db, db_item, event)
            task = await workshop_service.start_workshop_task(db, workshop_id=workshop_id, collection_id=db_item.id)
            asyncio.create_task(workshop_service.run_workshop_task(db, task_id=task.id))
        except Exception:
            logger.exception("Failed to create task for favorite_item_id=%s", getattr(db_item, "id", None))


from client_sdk.params import TaskParams, ServiceParams


async def _build_known_briefs(db: AsyncSessionLocal, collection_id: str) -> List[Dict[str, Any]]:
    """DRY Helper: Build the list of known brief items for delta detection."""
    known_briefs = []
    try:
        existing_items = (
            (await db.execute(select(FavoriteItem).where(FavoriteItem.collection_id == collection_id)))
            .scalars()
            .all()
        )
        for it in existing_items:
            known_briefs.append(
                {
                    "id": it.platform_favorite_id,
                    "bvid": it.platform_item_id,
                }
            )
    except Exception:
        logger.exception("Failed building known_briefs for collection_id=%s", collection_id)
    return known_briefs


def _get_plugin_config_for_platform(platform: str) -> Tuple[str, str, int, List[str], List[str]]:
    """Get plugin configuration for a given platform.

    Returns: (plugin_id, stream_group, interval, cookie_ids, fingerprint_fields)
    """
    if platform == "bilibili":
        return (
            settings.BILIBILI_FAVORITES_PLUGIN_ID,
            settings.BILIBILI_FAVORITES_STREAM_GROUP,
            settings.BILIBILI_FAVORITES_STREAM_INTERVAL,
            settings.BILIBILI_COOKIE_IDS,
            settings.BILIBILI_FINGERPRINT_FIELDS,
        )
    elif platform == "xiaohongshu":
        return (
            settings.XIAOHONGSHU_FAVORITES_PLUGIN_ID,
            f"{settings.XIAOHONGSHU_FAVORITES_PLUGIN_ID}-updates",
            settings.XIAOHONGSHU_STREAM_INTERVAL,
            settings.XIAOHONGSHU_COOKIE_IDS,
            ["id", "note_id"],  # XHS fingerprint fields
        )
    else:
        logger.warning(f"Unknown platform: {platform}, using bilibili defaults")
        return (
            settings.BILIBILI_FAVORITES_PLUGIN_ID,
            settings.BILIBILI_FAVORITES_STREAM_GROUP,
            settings.BILIBILI_FAVORITES_STREAM_INTERVAL,
            settings.BILIBILI_COOKIE_IDS,
            settings.BILIBILI_FINGERPRINT_FIELDS,
        )


async def _update_stream_for_collection(db: AsyncSessionLocal, collection: Collection, enabled: bool):
    """DRY Helper: Start or stop a stream for a given collection based on the enabled flag."""
    stream_id = f"{collection.platform}-col-{collection.id}"

    if not enabled:
        stream_manager.stop_stream(stream_id)
        logger.info(f"Stopped stream {stream_id} for collection {collection.title}")
        return

    # Get platform-specific configuration
    plugin_id, stream_group, interval, cookie_ids, fingerprint_fields = _get_plugin_config_for_platform(collection.platform)

    known_briefs = await _build_known_briefs(db, collection.platform_collection_id)

    stream_manager.start_stream(
        stream_id=stream_id,
        plugin_id=plugin_id,
        group=stream_group,
        run_mode="recurring",
        interval=float(interval),
        buffer_size=200,
        params={
            "task_params": TaskParams(
                cookie_ids=cookie_ids,
                close_page_when_task_finished=settings.BILIBILI_CLOSE_PAGE_WHEN_TASK_FINISHED
            ),
            "service_params": ServiceParams(max_items=10),
            "collection_id": collection.platform_collection_id,
            "storage_data": json.dumps(known_briefs, ensure_ascii=False),
            "fingerprint_fields": fingerprint_fields,
        },
    )
    logger.info(f"Started stream {stream_id} for collection {collection.title} on platform {collection.platform}")


async def _get_collections_for_workshop(db: AsyncSessionLocal, workshop: WorkshopModel) -> List[Collection]:
    """DRY Helper: Find all collections associated with a workshop via platform_bindings.

    New structure in executor_config:
    {
        "listening_enabled": true,
        "platform_bindings": [
            {"platform": "bilibili", "collection_ids": [1, 2, 3]},
            {"platform": "xiaohongshu", "collection_ids": [4, 5]}
        ]
    }

    Falls back to old single-binding structure for backward compatibility.
    """
    cfg = await _parse_executor_config(workshop) or {}
    collections: List[Collection] = []

    # New structure: platform_bindings (multi-platform, multi-collection)
    platform_bindings = cfg.get("platform_bindings", [])
    if platform_bindings and isinstance(platform_bindings, list):
        for binding in platform_bindings:
            platform = binding.get("platform")
            collection_ids = binding.get("collection_ids", [])

            if not collection_ids:
                continue

            # Fetch collections by IDs
            for col_id in collection_ids:
                col = await db.get(Collection, col_id)
                if col and col.platform == platform:
                    collections.append(col)

        if collections:
            return collections

    # Legacy fallback: single binding_collection_id
    bound_id = cfg.get("binding_collection_id")
    if bound_id is not None:
        collection = await db.get(Collection, bound_id)
        if collection:
            return [collection]

    # Legacy fallback: title match
    matched = (
        (await db.execute(select(Collection).where(Collection.title == workshop.name)))
        .scalars()
        .first()
    )
    if matched:
        return [matched]

    return []


async def handle_stream_event(event: Dict[str, Any]) -> None:
    """
    Route stream events to the appropriate platform handler.

    Detects platform from plugin_id and delegates to the corresponding orchestrator:
    - Xiaohongshu events -> XiaohongshuStreamEventOrchestrator
    - Bilibili events (default) -> StreamEventOrchestrator
    """
    plugin_id = event.get("plugin_id", "")

    # Route to platform-specific orchestrator
    if "xiaohongshu" in plugin_id.lower():
        from app.services.xiaohongshu_event_handler import create_xiaohongshu_event_orchestrator
        logger.info(f"Routing event to Xiaohongshu handler (plugin_id: {plugin_id})")
        orchestrator = create_xiaohongshu_event_orchestrator()
    else:
        # Default to Bilibili handler
        from app.services.stream_event_handler import create_bilibili_event_orchestrator
        logger.info(f"Routing event to Bilibili handler (plugin_id: {plugin_id})")
        orchestrator = create_bilibili_event_orchestrator()

    async with AsyncSessionLocal() as db:
        await orchestrator.handle_event(event, db)


async def start_enabled_workshop_streams() -> None:
    """Start streams for all workshops that have listening enabled."""
    try:
        async with AsyncSessionLocal() as db:
            workshops = (await db.execute(select(WorkshopModel))).scalars().all()
            for ws in workshops:
                cfg = await _parse_executor_config(ws)
                if not (isinstance(cfg, dict) and cfg.get("listening_enabled")):
                    continue

                # Get all collections for this workshop (supports multi-platform, multi-collection)
                collections = await _get_collections_for_workshop(db, ws)
                for collection in collections:
                    await _update_stream_for_collection(db, collection, enabled=True)

                if collections:
                    logger.info(f"Started {len(collections)} stream(s) for workshop '{ws.name}'")
                else:
                    logger.warning(f"Workshop '{ws.name}' has listening enabled but no collections bound")
    except Exception:
        logger.exception("Failed to start enabled workshop streams")


async def toggle_workshop_listening(db, workshop_id: str, enabled: bool, workshop_name: Optional[str] = None) -> Dict[str, Any]:
    """Enable or disable listening for a workshop and update all its streams.

    This will start/stop streams for ALL collections bound to this workshop.
    """
    row = (
        (await db.execute(select(WorkshopModel).where(WorkshopModel.workshop_id == workshop_id)))
        .scalars()
        .first()
    )
    if not row:
        return {"ok": False, "error": "workshop_not_found"}

    cfg = await _parse_executor_config(row) or {}
    cfg["listening_enabled"] = bool(enabled)
    row.executor_config = json.dumps(cfg, ensure_ascii=False)
    db.add(row)
    await db.commit()
    await db.refresh(row)

    # After committing the state change, find ALL associated collections and update their streams
    collections = await _get_collections_for_workshop(db, row)
    streams_updated = 0

    for collection in collections:
        await _update_stream_for_collection(db, collection, enabled=enabled)
        streams_updated += 1

    if enabled and streams_updated == 0:
        logger.warning(f"Workshop '{workshop_id}' enabled but no collections bound")

    return {
        "ok": True,
        "listening_enabled": bool(enabled),
        "streams_updated": streams_updated,
        "collections": [{"id": c.id, "title": c.title, "platform": c.platform} for c in collections]
    }


