"""
Stream Event Handler Module

This module provides a clean, maintainable architecture for handling stream events
from external plugins. It follows SOLID principles and clean architecture patterns.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.db import models
from app.db.models import FavoriteItem

logger = get_logger(__name__)


# ============================================================================
# Data Transfer Objects (DTOs)
# ============================================================================

@dataclass
class PersistResult:
    """Result of item persistence operation."""
    newly_created: List[FavoriteItem]
    needs_recovery: List[FavoriteItem]

    @property
    def all_items(self) -> List[FavoriteItem]:
        """All items that need processing."""
        return self.newly_created + self.needs_recovery

    @property
    def total_count(self) -> int:
        """Total number of items."""
        return len(self.newly_created) + len(self.needs_recovery)


@dataclass
class CreatorInfo:
    """Creator/Author information from stream event."""
    user_id: str
    username: str
    avatar: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CreatorInfo":
        """Factory method to create from raw dict."""
        return cls(
            user_id=str(data.get("user_id", "")),
            username=str(data.get("username", "")),
            avatar=str(data.get("avatar", ""))
        )


@dataclass
class VideoItemBrief:
    """Brief video information from stream event."""
    bvid: str
    collection_id: str
    title: str
    intro: str
    cover: str
    fav_time: int
    creator: CreatorInfo
    favorite_id: Optional[str] = None
    pubdate: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], fallback_collection_id: str = "") -> Optional["VideoItemBrief"]:
        """Factory method to create from raw dict. Returns None if invalid.

        Args:
            data: Raw video item data from RPC
            fallback_collection_id: Collection ID from event params (used if item doesn't have it)
        """
        bvid = str(data.get("bvid", ""))
        if not bvid:
            return None

        creator_data = data.get("creator") or {}

        # Extract favorite_id (platform's favorite record ID)
        favorite_id = data.get("id")
        if favorite_id is not None:
            favorite_id = str(favorite_id)

        # Extract pubdate (publish timestamp)
        pubdate = data.get("pubdate")
        if pubdate is not None:
            try:
                pubdate = int(pubdate)
            except (ValueError, TypeError):
                pubdate = None

        # Extract collection_id: prefer item's own, fallback to event params
        collection_id = str(data.get("collection_id", "") or fallback_collection_id)

        return cls(
            bvid=bvid,
            collection_id=collection_id,
            title=str(data.get("title", "")),
            intro=str(data.get("intro", "")),
            cover=str(data.get("cover", "")),
            fav_time=int(data.get("fav_time", 0)),
            creator=CreatorInfo.from_dict(creator_data),
            favorite_id=favorite_id,
            pubdate=pubdate
        )


@dataclass
class StreamEventData:
    """Parsed stream event data."""
    items: List[VideoItemBrief]
    event_metadata: Dict[str, Any]

    @property
    def has_items(self) -> bool:
        """Check if event contains any items."""
        return bool(self.items)


# ============================================================================
# Abstract Base Classes / Protocols
# ============================================================================

class EventParser(Protocol):
    """Protocol for parsing stream events."""
    
    def parse(self, event: Dict[str, Any]) -> StreamEventData:
        """Parse raw event into structured data."""
        ...


class ItemPersister(Protocol):
    """Protocol for persisting items to database."""

    async def persist_brief_items(
        self,
        db: AsyncSession,
        items: List[VideoItemBrief]
    ) -> PersistResult:
        """Persist brief items, distinguishing new vs existing items needing recovery."""
        ...


class DetailsSyncer(Protocol):
    """Protocol for syncing item details."""
    
    async def sync_details(
        self, 
        db: AsyncSession, 
        items: List[FavoriteItem]
    ) -> None:
        """Sync detailed information for items."""
        ...


class TaskCreator(Protocol):
    """Protocol for creating analysis tasks."""
    
    async def create_analysis_tasks(
        self, 
        db: AsyncSession, 
        items: List[FavoriteItem],
        event_metadata: Dict[str, Any]
    ) -> None:
        """Create analysis tasks for items with details."""
        ...


# ============================================================================
# Concrete Implementations
# ============================================================================

class BilibiliEventParser:
    """Parser for Bilibili plugin stream events."""

    def parse(self, event: Dict[str, Any]) -> StreamEventData:
        """
        Parse Bilibili stream event.

        Expected structure:
        {
            "params": {
                "collection_id": "...",  # Fallback if items don't contain it
                ...
            },
            "payload": {
                "result": {
                    "success": true,
                    "data": {
                        "added": {"data": [...]},
                        "data": [...]
                    }
                }
            }
        }
        """
        # Extract fallback collection_id from params (used if item doesn't have it)
        params = event.get("params") or {}
        fallback_collection_id = str(params.get("collection_id", ""))

        items = self._extract_items(event)
        video_items = self._parse_items(items, fallback_collection_id)

        return StreamEventData(
            items=video_items,
            event_metadata=event
        )
    
    def _extract_items(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract raw item dicts from event structure."""
        try:
            payload = event.get("payload", {})
            if not isinstance(payload, dict):
                return []
            
            result = payload.get("result", {})
            if not isinstance(result, dict) or not result.get("success"):
                return []
            
            data = result.get("data", {})
            if not isinstance(data, dict):
                return []
            
            # Prefer added items, fallback to all items
            added = data.get("added", {})
            if isinstance(added, dict):
                added_items = added.get("data", [])
                if isinstance(added_items, list) and added_items:
                    return added_items
            
            all_items = data.get("data", [])
            return all_items if isinstance(all_items, list) else []
            
        except Exception as e:
            logger.warning(f"Failed to extract items from event: {e}")
            return []
    
    def _parse_items(self, items: List[Dict[str, Any]], fallback_collection_id: str = "") -> List[VideoItemBrief]:
        """Parse raw items into VideoItemBrief objects.

        Args:
            items: Raw video items from RPC
            fallback_collection_id: Collection ID from event params (used if items don't have it)
        """
        parsed = []
        for item in items:
            try:
                video_item = VideoItemBrief.from_dict(item, fallback_collection_id)
                if video_item:
                    parsed.append(video_item)
            except Exception as e:
                logger.warning(f"Failed to parse item: {e}")
        return parsed


class BilibiliItemPersister:
    """Handles persistence of Bilibili items to database."""

    def __init__(self, crud_favorites):
        """
        Initialize with CRUD dependencies.

        Args:
            crud_favorites: CRUD module for favorites operations
        """
        self.crud = crud_favorites

    async def persist_brief_items(
        self,
        db: AsyncSession,
        items: List[VideoItemBrief]
    ) -> PersistResult:
        """
        Persist brief items to database idempotently with recovery detection.

        Returns:
            PersistResult distinguishing newly created vs items needing recovery
        """
        newly_created = []
        needs_recovery = []

        for item in items:
            try:
                result = await self._persist_single_item(db, item)
                if result:
                    if result.get("is_new"):
                        newly_created.append(result["item"])
                    else:
                        needs_recovery.append(result["item"])
            except Exception as e:
                logger.error(f"Failed to persist item {item.bvid}: {e}")

        return PersistResult(
            newly_created=newly_created,
            needs_recovery=needs_recovery
        )
    
    async def _persist_single_item(
        self,
        db: AsyncSession,
        item: VideoItemBrief
    ) -> Optional[Dict[str, Any]]:
        """Persist a single item with recovery detection.

        Returns:
            Dict with "item" (FavoriteItem) and "is_new" (bool), or None if skipped
        """
        # Check if already exists
        existing = await self.crud.favorite_item.get_by_platform_item_id(
            db, platform_item_id=item.bvid
        )
        if existing:
            # Check if needs recovery
            if await self._needs_recovery(db, existing):
                logger.info(
                    f"Video {item.bvid} exists but needs recovery "
                    f"(incomplete details or task)"
                )
                return {"item": existing, "is_new": False}
            else:
                logger.debug(f"Video {item.bvid} already fully processed, skipping")
                return None
        
        # Ensure author exists
        author = await self._ensure_author(db, item.creator)
        
        # Find collection if specified
        collection = await self._find_collection(db, item.collection_id)
        
        # Create the item
        from app.schemas.unified import FavoriteItemCreate
        
        # Build item schema with all available fields
        item_schema = FavoriteItemCreate(
            platform_item_id=item.bvid,
            platform=models.PlatformEnum.bilibili,
            item_type=models.ItemTypeEnum.video,
            title=item.title,
            intro=item.intro,
            cover_url=item.cover,
            favorited_at=datetime.fromtimestamp(item.fav_time),
            published_at=datetime.fromtimestamp(item.pubdate) if item.pubdate else None,
        )
        
        # Create using dict to manually add fields not in schema
        item_dict = item_schema.dict()
        db_item = models.FavoriteItem(
            **item_dict,
            author_id=author.id,
            collection_id=item.collection_id,  # Platform collection ID (foreign key to collections.platform_collection_id)
            platform_favorite_id=item.favorite_id,
        )
        
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item)

        return {"item": db_item, "is_new": True}
    
    async def _ensure_author(
        self, 
        db: AsyncSession, 
        creator: CreatorInfo
    ) -> models.Author:
        """Ensure author exists in database."""
        existing = await self.crud.author.get_by_platform_id(
            db,
            platform=models.PlatformEnum.bilibili,
            platform_user_id=creator.user_id
        )
        
        if existing:
            return existing
        
        from app.schemas.unified import AuthorCreate
        
        return await self.crud.author.create(
            db,
            obj_in=AuthorCreate(
                platform_user_id=creator.user_id,
                platform=models.PlatformEnum.bilibili,
                username=creator.username,
                avatar_url=creator.avatar
            )
        )
    
    async def _find_collection(
        self,
        db: AsyncSession,
        collection_id: str
    ) -> Optional[models.Collection]:
        """Find collection by platform ID if exists."""
        if not collection_id:
            return None

        return await self.crud.collection.get_by_platform_id(
            db,
            platform=models.PlatformEnum.bilibili,
            platform_collection_id=collection_id
        )

    async def _needs_recovery(self, db: AsyncSession, item: models.FavoriteItem) -> bool:
        """Check if an existing item needs recovery (incomplete processing).

        An item needs recovery if:
        1. It has no details (and not exhausted retry attempts)
        2. It has details but no task at all (neither success nor unfinished)

        Returns:
            True if item needs recovery processing
        """
        from app.crud import crud_tasks
        from app.core.config import settings
        from sqlalchemy import select

        # Check 1: Missing details
        has_details = (
            item.bilibili_video_details is not None
        )

        if not has_details:
            # Allow recovery if not exhausted attempts
            max_attempts = getattr(settings, 'BILIBILI_DETAILS_MAX_RETRY_ATTEMPTS', 5)
            if (item.details_fetch_attempts or 0) < max_attempts:
                return True
            # Or if last attempt was more than 24 hours ago
            if item.details_last_attempt_at:
                hours_since_attempt = (
                    datetime.utcnow() - item.details_last_attempt_at
                ).total_seconds() / 3600
                if hours_since_attempt > 24:
                    return True
            return False

        # Check 2: Has details but no task at all (check ANY task, not just unfinished)
        # ⚠️ CRITICAL FIX: If item already has SUCCESS task, no recovery needed!
        any_task = await db.execute(
            select(models.Task).where(
                models.Task.favorite_item_id == item.id
            ).limit(1)
        )
        has_any_task = any_task.scalars().first() is not None

        # Needs recovery only if has details but NO task at all
        return not has_any_task


class BilibiliDetailsSyncer:
    """Handles syncing of detailed information for items."""
    
    def __init__(self, favorites_service):
        """
        Initialize with service dependencies.
        
        Args:
            favorites_service: Service for syncing video details
        """
        self.favorites_service = favorites_service
    
    async def sync_details(
        self, 
        db: AsyncSession, 
        items: List[FavoriteItem]
    ) -> None:
        """
        Sync detailed information for items.
        
        This calls the favorites service to fetch and persist
        detailed information from external APIs.
        """
        bvids = [
            item.platform_item_id 
            for item in items 
            if hasattr(item, 'platform_item_id')
        ]
        
        if not bvids:
            logger.info("No items to sync details for")
            return
        
        try:
            logger.info(f"Syncing details for {len(bvids)} items")
            await self.favorites_service.sync_bilibili_videos_details(
                db, 
                bvids=bvids
            )
            logger.info("Details sync completed successfully")
        except Exception as e:
            logger.error(f"Failed to sync details: {e}")
            # Don't re-raise - allow partial success


class WorkshopTaskCreator:
    """Creates analysis tasks for items."""
    
    def __init__(self, crud_favorites, workshop_service):
        """
        Initialize with service dependencies.
        
        Args:
            crud_favorites: CRUD module for database operations
            workshop_service: Service for creating workshop tasks
        """
        self.crud = crud_favorites
        self.workshop_service = workshop_service
    
    async def create_analysis_tasks(
        self, 
        db: AsyncSession, 
        items: List[FavoriteItem],
        event_metadata: Dict[str, Any]
    ) -> None:
        """
        Create analysis tasks for items that have details.
        
        Tasks are only created if:
        1. Item has detailed information
        2. No pending/in-progress task exists
        """
        for item in items:
            try:
                await self._create_task_if_eligible(db, item, event_metadata)
            except Exception as e:
                logger.error(f"Failed to create task for item {item.id}: {e}")
    
    async def _create_task_if_eligible(
        self, 
        db: AsyncSession, 
        item: FavoriteItem,
        event_metadata: Dict[str, Any]
    ) -> None:
        """Create task for single item if eligible."""
        # Check if item has details
        if not await self._has_details(db, item):
            logger.debug(f"Item {item.platform_item_id} has no details, skipping task")
            return
        
        # Check for existing task
        if await self._has_pending_task(db, item):
            logger.debug(f"Item {item.id} already has pending task, skipping")
            return
        
        # Resolve workshop and create task
        workshop_id = await self._resolve_workshop_id(db, item, event_metadata)
        
        task = await self.workshop_service.start_workshop_task(
            db, 
            workshop_id=workshop_id, 
            collection_id=item.id
        )
        
        # Run task asynchronously (creates its own DB session)
        asyncio.create_task(
            self.workshop_service.run_workshop_task(task_id=task.id)
        )
        
        logger.info(f"Created task {task.id} for item {item.id}")
    
    async def _has_details(self, db: AsyncSession, item: FavoriteItem) -> bool:
        """Check if item has detailed information."""
        full_item = await self.crud.favorite_item.get_by_platform_item_id_with_details(
            db, 
            platform_item_id=item.platform_item_id
        )
        return bool(
            full_item and 
            hasattr(full_item, 'bilibili_video_details') and 
            full_item.bilibili_video_details
        )
    
    async def _has_pending_task(self, db: AsyncSession, item: FavoriteItem) -> bool:
        """Check if item has ANY existing task (including SUCCESS).

        ⚠️ CRITICAL FIX: This checks for ANY task, not just PENDING/IN_PROGRESS.
        If item already has a SUCCESS task, we should NOT create duplicate!
        """
        from sqlalchemy import select
        from app.db.models import Task as TaskModel

        result = await db.execute(
            select(TaskModel).where(
                TaskModel.favorite_item_id == item.id
            ).limit(1)
        )
        return result.scalars().first() is not None
    
    async def _resolve_workshop_id(
        self, 
        db: AsyncSession, 
        item: FavoriteItem,
        event_metadata: Dict[str, Any]
    ) -> str:
        """Resolve which workshop to use for the item."""
        # This is a simplified version - implement your business logic
        from app.services.listener_service import _resolve_workshop_id_for_item
        return await _resolve_workshop_id_for_item(db, item, event_metadata)


# ============================================================================
# Main Orchestrator
# ============================================================================

class StreamEventOrchestrator:
    """
    Main orchestrator for handling stream events.

    This class coordinates the entire event processing pipeline
    following clean architecture principles.
    """

    def __init__(
        self,
        parser: EventParser,
        persister: ItemPersister,
        syncer: DetailsSyncer,
        task_creator: TaskCreator,
        first_sync_threshold: Optional[int] = None
    ):
        """
        Initialize with all dependencies.

        Args:
            parser: Event parser implementation
            persister: Item persistence implementation
            syncer: Details syncing implementation
            task_creator: Task creation implementation
            first_sync_threshold: Threshold for first sync detection (default: from config)
        """
        from app.core.config import settings

        self.parser = parser
        self.persister = persister
        self.syncer = syncer
        self.task_creator = task_creator
        self.first_sync_threshold = first_sync_threshold or settings.FIRST_SYNC_THRESHOLD
    
    async def handle_event(self, event: Dict[str, Any], db: AsyncSession) -> None:
        """
        Main entry point for handling stream events.

        Pipeline:
        1. Parse event into structured data
        2. Persist brief items to database (with recovery detection)
        3. Check for first sync (skip AI processing if threshold exceeded)
        4. Sync detailed information
        5. Create analysis tasks
        """
        try:
            # Step 1: Parse event
            event_data = self.parser.parse(event)
            if not event_data.has_items:
                logger.debug("No items in event, skipping")
                return

            logger.info(f"Processing {len(event_data.items)} items from event")

            # Step 2: Persist brief items (with recovery detection)
            persist_result = await self.persister.persist_brief_items(
                db,
                event_data.items
            )

            logger.info(
                f"Persistence result: {len(persist_result.newly_created)} new, "
                f"{len(persist_result.needs_recovery)} need recovery, "
                f"{persist_result.total_count} total"
            )

            if persist_result.total_count == 0:
                logger.info("No items to process")
                return

            # Step 3: Check for first sync (skip AI processing if too many new items)
            if self._is_first_sync(persist_result):
                logger.warning(
                    f"⚠️  First sync detected: {len(persist_result.newly_created)} new items "
                    f"exceeds threshold ({self.first_sync_threshold}). "
                    f"Skipping AI processing to avoid overwhelming the system."
                )
                return

            # Step 4: Sync details
            await self.syncer.sync_details(db, persist_result.all_items)

            # Step 5: Create tasks
            await self.task_creator.create_analysis_tasks(
                db,
                persist_result.all_items,
                event_data.event_metadata
            )

            logger.info("Event processing completed successfully")

        except Exception as e:
            logger.error(f"Failed to process event: {e}", exc_info=True)
            # Don't re-raise - allow system to continue

    def _is_first_sync(self, persist_result: PersistResult) -> bool:
        """Detect if this is a first sync based on newly created item count.

        First sync is detected when newly created items exceed the configured threshold.
        This prevents overwhelming the system with AI tasks on initial sync.

        Args:
            persist_result: Result from persistence operation

        Returns:
            True if this appears to be a first sync (skip AI processing)
        """
        newly_created_count = len(persist_result.newly_created)
        return newly_created_count > self.first_sync_threshold


# ============================================================================
# Factory Function
# ============================================================================

def create_bilibili_event_orchestrator(
    first_sync_threshold: Optional[int] = None
) -> StreamEventOrchestrator:
    """
    Factory function to create a configured Bilibili event orchestrator.

    Args:
        first_sync_threshold: Threshold for first sync detection (default: from config)

    Returns:
        Configured orchestrator instance
    """
    from app.crud import crud_favorites
    from app.services import favorites_service, workshop_service

    return StreamEventOrchestrator(
        parser=BilibiliEventParser(),
        persister=BilibiliItemPersister(crud_favorites),
        syncer=BilibiliDetailsSyncer(favorites_service),
        task_creator=WorkshopTaskCreator(crud_favorites, workshop_service),
        first_sync_threshold=first_sync_threshold
    )
