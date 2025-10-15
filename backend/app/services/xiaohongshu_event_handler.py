"""
Xiaohongshu Stream Event Handler with Retry Mechanism.

This module handles Xiaohongshu favorite events with intelligent retry logic
for details fetching, which commonly fails due to platform restrictions.
"""

import asyncio
import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import get_logger
from app.crud import crud_favorites
from app.db import models
from app.db.base import AsyncSessionLocal
from app.schemas.unified import AuthorCreate, FavoriteItemCreate
from app.services import favorites_service, workshop_service

logger = get_logger(__name__)


# ============================================================================
# Data Transfer Objects (DTOs)
# ============================================================================

@dataclass
class XiaohongshuCreatorInfo:
    """Creator information from Xiaohongshu event."""
    user_id: str
    username: str
    avatar: str
    xsec_token: Optional[str] = None


@dataclass
class XiaohongshuNoteItemBrief:
    """Brief note information from Xiaohongshu stream event."""
    note_id: str
    xsec_token: str
    collection_id: str
    title: str
    cover_image: str
    creator: XiaohongshuCreatorInfo
    fav_time: str
    statistic: Optional[Dict[str, Any]] = None


@dataclass
class XiaohongshuStreamEventData:
    """Parsed Xiaohongshu stream event data."""
    items: List[XiaohongshuNoteItemBrief]
    event_metadata: Dict[str, Any]


# ============================================================================
# Protocol Interfaces
# ============================================================================

class XiaohongshuEventParser(Protocol):
    """Parse raw Xiaohongshu stream events."""

    async def parse(self, event: Dict[str, Any]) -> XiaohongshuStreamEventData:
        """Parse event into structured data."""
        ...


class XiaohongshuItemPersister(Protocol):
    """Persist brief Xiaohongshu note items to database."""

    async def persist_brief_items(
        self, db: AsyncSession, items: List[XiaohongshuNoteItemBrief]
    ) -> List[models.FavoriteItem]:
        """Persist brief items, returning created/existing FavoriteItem records."""
        ...


class XiaohongshuDetailsSyncer(Protocol):
    """Sync detailed information for Xiaohongshu notes with retry support."""

    async def sync_details(
        self, db: AsyncSession, items: List[models.FavoriteItem]
    ) -> List[models.FavoriteItem]:
        """Sync details for items, returning items with successfully fetched details."""
        ...


class XiaohongshuTaskCreator(Protocol):
    """Create workshop tasks for Xiaohongshu notes."""

    async def create_analysis_tasks(
        self,
        db: AsyncSession,
        items: List[models.FavoriteItem],
        event_metadata: Dict[str, Any]
    ) -> None:
        """Create analysis tasks for items that have details."""
        ...


# ============================================================================
# Concrete Implementations
# ============================================================================

class DefaultXiaohongshuEventParser:
    """Default parser for Xiaohongshu stream events."""

    async def parse(self, event: Dict[str, Any]) -> XiaohongshuStreamEventData:
        """Parse Xiaohongshu event structure."""
        payload = event.get("payload") or {}
        result = payload.get("result") if isinstance(payload, dict) else None

        if not isinstance(result, dict) or not result.get("success"):
            return XiaohongshuStreamEventData(items=[], event_metadata=event)

        data_block = result.get("data") or {}

        # Prefer 'added' items, fallback to all items
        added_block = (data_block.get("added") or {}) if isinstance(data_block, dict) else {}
        items_added = (added_block.get("data") or []) if isinstance(added_block, dict) else []
        all_items = (data_block.get("data") or []) if isinstance(data_block, dict) else []
        raw_items = items_added if items_added else all_items

        notes = []
        for raw in raw_items:
            try:
                creator_raw = raw.get("author_info", {}) or {}
                note = XiaohongshuNoteItemBrief(
                    note_id=str(raw.get("id") or raw.get("note_id")),
                    xsec_token=raw.get("xsec_token", ""),
                    collection_id=str(raw.get("collection_id", "")),
                    title=raw.get("title", ""),
                    cover_image=raw.get("cover_image", ""),
                    creator=XiaohongshuCreatorInfo(
                        user_id=str(creator_raw.get("user_id", "")),
                        username=creator_raw.get("username", ""),
                        avatar=creator_raw.get("avatar", ""),
                        xsec_token=creator_raw.get("xsec_token")
                    ),
                    fav_time=str(raw.get("fav_time", "0")),
                    statistic=raw.get("statistic")
                )
                notes.append(note)
            except Exception as e:
                logger.exception(f"Failed to parse Xiaohongshu note item: {e}")
                continue

        return XiaohongshuStreamEventData(items=notes, event_metadata=event)


class DefaultXiaohongshuItemPersister:
    """Default persister for Xiaohongshu note brief items."""

    async def persist_brief_items(
        self, db: AsyncSession, items: List[XiaohongshuNoteItemBrief]
    ) -> List[models.FavoriteItem]:
        """Idempotently persist brief note items."""
        ingested = []

        for note in items:
            try:
                # Check if already exists
                existing = await crud_favorites.favorite_item.get_by_platform_item_id(
                    db, platform_item_id=note.note_id
                )
                if existing:
                    ingested.append(existing)
                    continue

                # Ensure author exists
                db_author = await crud_favorites.author.get_by_platform_id(
                    db,
                    platform=models.PlatformEnum.xiaohongshu,
                    platform_user_id=note.creator.user_id
                )
                if not db_author:
                    db_author = await crud_favorites.author.create(
                        db,
                        obj_in=AuthorCreate(
                            platform_user_id=note.creator.user_id,
                            platform=models.PlatformEnum.xiaohongshu,
                            username=note.creator.username,
                            avatar_url=note.creator.avatar
                        )
                    )

                # Get collection if exists
                db_collection = None
                if note.collection_id:
                    db_collection = await crud_favorites.collection.get_by_platform_id(
                        db,
                        platform=models.PlatformEnum.xiaohongshu,
                        platform_collection_id=note.collection_id
                    )

                # Parse favorited_at
                favorited_at = datetime.datetime.utcnow()
                try:
                    if note.fav_time and note.fav_time != "0":
                        favorited_at = datetime.datetime.fromtimestamp(int(note.fav_time))
                except (ValueError, TypeError):
                    pass

                # Create FavoriteItem
                item_in = FavoriteItemCreate(
                    platform_item_id=note.note_id,
                    platform=models.PlatformEnum.xiaohongshu,
                    item_type=models.ItemTypeEnum.note,
                    title=note.title,
                    intro="",  # Will be filled with desc from details
                    cover_url=note.cover_image,
                    favorited_at=favorited_at,
                    published_at=None  # Will be filled from details
                )

                db_item = await crud_favorites.favorite_item.create_brief_with_relationships(
                    db,
                    item_in=item_in,
                    author_id=db_author.id,
                    collection_id=db_collection.id if db_collection else None
                )

                # Store xsec_token in xiaohongshu_note_details for later use
                # Create a minimal details record with just xsec_token
                if note.xsec_token:
                    xhs_detail = models.XiaohongshuNoteDetail(
                        favorite_item_id=db_item.id,
                        note_id=note.note_id,
                        xsec_token=note.xsec_token,
                        desc="",  # Will be filled later
                        ip_location="",
                        published_date=""
                    )
                    db.add(xhs_detail)
                    await db.commit()
                    await db.refresh(db_item)

                ingested.append(db_item)

            except Exception as e:
                logger.exception(f"Failed to persist Xiaohongshu note {note.note_id}: {e}")
                continue

        return ingested


class DefaultXiaohongshuDetailsSyncer:
    """Default details syncer with retry mechanism for Xiaohongshu."""

    def __init__(self, retry_delay_minutes: int = 5, max_attempts: int = 5):
        """
        Initialize syncer.

        Args:
            retry_delay_minutes: Minutes to wait before retry if failed
            max_attempts: Maximum retry attempts per note
        """
        self.retry_delay_minutes = retry_delay_minutes
        self.max_attempts = max_attempts

    async def sync_details(
        self, db: AsyncSession, items: List[models.FavoriteItem]
    ) -> List[models.FavoriteItem]:
        """Sync details with intelligent retry logic."""
        items_with_details = []

        for db_item in items:
            try:
                # Check if details already exist
                if db_item.xiaohongshu_note_details and db_item.xiaohongshu_note_details.desc:
                    logger.info(f"Note {db_item.platform_item_id} already has details")
                    items_with_details.append(db_item)
                    continue

                # Check retry attempts
                if (db_item.details_fetch_attempts or 0) >= self.max_attempts:
                    logger.warning(
                        f"Note {db_item.platform_item_id} exceeded max retry attempts "
                        f"({self.max_attempts})"
                    )
                    continue

                # Check if we should retry (respect retry delay)
                if db_item.details_last_attempt_at:
                    time_since_last_attempt = (
                        datetime.datetime.utcnow() - db_item.details_last_attempt_at
                    )
                    retry_delay = datetime.timedelta(minutes=self.retry_delay_minutes)

                    if time_since_last_attempt < retry_delay:
                        logger.info(
                            f"Note {db_item.platform_item_id} waiting for retry delay "
                            f"({retry_delay - time_since_last_attempt} remaining)"
                        )
                        # Schedule retry task for later
                        asyncio.create_task(
                            self._schedule_retry(db_item.platform_item_id, retry_delay)
                        )
                        continue

                # Get xsec_token
                xsec_token = ""
                if db_item.xiaohongshu_note_details:
                    xsec_token = db_item.xiaohongshu_note_details.xsec_token or ""

                # Attempt to fetch details
                updated_item = await favorites_service.sync_xiaohongshu_note_details_single(
                    db,
                    note_id=db_item.platform_item_id,
                    xsec_token=xsec_token,
                    max_retry_attempts=self.max_attempts
                )

                if updated_item and updated_item.xiaohongshu_note_details:
                    logger.info(f"Successfully fetched details for note {db_item.platform_item_id}")
                    items_with_details.append(updated_item)
                else:
                    logger.warning(
                        f"Failed to fetch details for note {db_item.platform_item_id}, "
                        f"will retry later"
                    )
                    # Schedule retry
                    asyncio.create_task(
                        self._schedule_retry(
                            db_item.platform_item_id,
                            datetime.timedelta(minutes=self.retry_delay_minutes)
                        )
                    )

            except Exception as e:
                logger.exception(f"Exception syncing details for note {db_item.platform_item_id}: {e}")
                continue

        return items_with_details

    async def _schedule_retry(self, note_id: str, delay: datetime.timedelta):
        """Schedule a retry task after delay."""
        await asyncio.sleep(delay.total_seconds())
        logger.info(f"Retrying details fetch for note {note_id}")

        async with AsyncSessionLocal() as db:
            db_item = await crud_favorites.favorite_item.get_by_platform_item_id(
                db, platform_item_id=note_id
            )
            if not db_item:
                return

            xsec_token = ""
            if db_item.xiaohongshu_note_details:
                xsec_token = db_item.xiaohongshu_note_details.xsec_token or ""

            await favorites_service.sync_xiaohongshu_note_details_single(
                db,
                note_id=note_id,
                xsec_token=xsec_token,
                max_retry_attempts=self.max_attempts
            )


class DefaultXiaohongshuTaskCreator:
    """Default task creator for Xiaohongshu notes."""

    async def create_analysis_tasks(
        self,
        db: AsyncSession,
        items: List[models.FavoriteItem],
        event_metadata: Dict[str, Any]
    ) -> None:
        """Create workshop tasks only for items with successful details."""
        from app.crud import crud_tasks

        for db_item in items:
            try:
                # Verify details exist
                if not db_item.xiaohongshu_note_details or not db_item.xiaohongshu_note_details.desc:
                    logger.info(
                        f"Skipping task creation for note {db_item.platform_item_id}: "
                        f"details not available"
                    )
                    continue

                # Check for existing unfinished tasks
                existing_task = await crud_tasks.task.get_unfinished_task_for_item(
                    db, favorite_item_id=db_item.id
                )
                if existing_task:
                    logger.info(
                        f"Note {db_item.platform_item_id} already has unfinished task {existing_task.id}"
                    )
                    continue

                # Resolve workshop_id from collection or default
                workshop_id = await self._resolve_workshop_id(db, db_item, event_metadata)

                # Create workshop task
                task = await workshop_service.start_workshop_task(
                    db, workshop_id=workshop_id, collection_id=db_item.id
                )

                # Run task in background
                asyncio.create_task(workshop_service.run_workshop_task(db, task_id=task.id))

                logger.info(
                    f"Created workshop task {task.id} for note {db_item.platform_item_id} "
                    f"using workshop '{workshop_id}'"
                )

            except Exception as e:
                logger.exception(f"Failed to create task for note {db_item.platform_item_id}: {e}")
                continue

    async def _resolve_workshop_id(
        self, db: AsyncSession, db_item: models.FavoriteItem, event: Dict[str, Any]
    ) -> str:
        """Resolve workshop ID from collection binding or defaults."""
        from app.core.runtime_config import runtime_config

        # Default workshop
        default_workshop = "summary-01"

        try:
            # Check collection-based workshop binding
            if db_item.collection_id:
                collection = await db.get(models.Collection, db_item.collection_id)
                if collection:
                    # Check for workshop with matching binding
                    workshops = (
                        (await db.execute(select(models.Workshop))).scalars().all()
                    )
                    for ws in workshops:
                        try:
                            import json
                            cfg = json.loads(ws.executor_config) if ws.executor_config else {}
                            if cfg.get("listening_enabled"):
                                # Check platform_bindings
                                platform_bindings = cfg.get("platform_bindings", [])
                                for binding in platform_bindings:
                                    if binding.get("platform") == "xiaohongshu":
                                        if collection.id in binding.get("collection_ids", []):
                                            return ws.workshop_id
                        except Exception:
                            continue

            # Fallback to runtime config category mapping
            category = (event.get("item") or {}).get("category") or event.get("category")
            mapping = runtime_config.get_category_map()
            return mapping.get(category or "", default_workshop)

        except Exception:
            logger.exception(f"Failed to resolve workshop for note {db_item.id}")
            return default_workshop


# ============================================================================
# Orchestrator
# ============================================================================

class XiaohongshuStreamEventOrchestrator:
    """Orchestrates Xiaohongshu stream event processing with clean dependencies."""

    def __init__(
        self,
        parser: XiaohongshuEventParser,
        persister: XiaohongshuItemPersister,
        syncer: XiaohongshuDetailsSyncer,
        task_creator: XiaohongshuTaskCreator
    ):
        self.parser = parser
        self.persister = persister
        self.syncer = syncer
        self.task_creator = task_creator

    async def handle_event(self, event: Dict[str, Any], db: AsyncSession) -> None:
        """
        Handle Xiaohongshu stream event with ordered pipeline:
        1. Parse event
        2. Persist brief items
        3. Sync details (with retry support)
        4. Create tasks (only for items with details)
        """
        logger.info("Processing Xiaohongshu stream event")

        # Step 1: Parse
        event_data = await self.parser.parse(event)
        if not event_data.items:
            logger.info("No items to process in event")
            return

        logger.info(f"Parsed {len(event_data.items)} Xiaohongshu notes from event")

        # Step 2: Persist brief items
        db_items = await self.persister.persist_brief_items(db, event_data.items)
        logger.info(f"Persisted {len(db_items)} note items")

        if not db_items:
            return

        # Step 3: Sync details (with retry mechanism)
        items_with_details = await self.syncer.sync_details(db, db_items)
        logger.info(
            f"Successfully fetched details for {len(items_with_details)}/{len(db_items)} notes"
        )

        # Step 4: Create tasks (only for items with details)
        if items_with_details:
            await self.task_creator.create_analysis_tasks(
                db, items_with_details, event_data.event_metadata
            )


# ============================================================================
# Factory Function
# ============================================================================

def create_xiaohongshu_event_orchestrator(
    retry_delay_minutes: int = 5,
    max_retry_attempts: int = 5
) -> XiaohongshuStreamEventOrchestrator:
    """
    Factory to create Xiaohongshu event orchestrator with default implementations.

    Args:
        retry_delay_minutes: Minutes to wait between retry attempts (default: 5)
        max_retry_attempts: Maximum retry attempts per note (default: 5)

    Returns:
        Configured orchestrator instance
    """
    return XiaohongshuStreamEventOrchestrator(
        parser=DefaultXiaohongshuEventParser(),
        persister=DefaultXiaohongshuItemPersister(),
        syncer=DefaultXiaohongshuDetailsSyncer(
            retry_delay_minutes=retry_delay_minutes,
            max_attempts=max_retry_attempts
        ),
        task_creator=DefaultXiaohongshuTaskCreator()
    )
