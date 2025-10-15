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
    def from_dict(cls, data: Dict[str, Any]) -> Optional["VideoItemBrief"]:
        """Factory method to create from raw dict. Returns None if invalid."""
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
        
        return cls(
            bvid=bvid,
            collection_id=str(data.get("collection_id", "")),
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
    ) -> List[FavoriteItem]:
        """Persist brief items and return database models."""
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
        items = self._extract_items(event)
        video_items = self._parse_items(items)
        
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
    
    def _parse_items(self, items: List[Dict[str, Any]]) -> List[VideoItemBrief]:
        """Parse raw items into VideoItemBrief objects."""
        parsed = []
        for item in items:
            try:
                video_item = VideoItemBrief.from_dict(item)
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
    ) -> List[FavoriteItem]:
        """
        Persist brief items to database idempotently.
        
        Returns:
            List of FavoriteItem models (both new and existing)
        """
        persisted = []
        
        for item in items:
            try:
                db_item = await self._persist_single_item(db, item)
                if db_item:
                    persisted.append(db_item)
            except Exception as e:
                logger.error(f"Failed to persist item {item.bvid}: {e}")
        
        return persisted
    
    async def _persist_single_item(
        self, 
        db: AsyncSession, 
        item: VideoItemBrief
    ) -> Optional[FavoriteItem]:
        """Persist a single item, returning existing if already present."""
        # Check if already exists
        existing = await self.crud.favorite_item.get_by_platform_item_id(
            db, platform_item_id=item.bvid
        )
        if existing:
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
        
        return db_item
    
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
        """Check if item has pending or in-progress task."""
        from sqlalchemy import select
        from app.db.models import Task as TaskModel, TaskStatus
        
        result = await db.execute(
            select(TaskModel).where(
                TaskModel.favorite_item_id == item.id,
                TaskModel.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
            )
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
        task_creator: TaskCreator
    ):
        """
        Initialize with all dependencies.
        
        Args:
            parser: Event parser implementation
            persister: Item persistence implementation
            syncer: Details syncing implementation
            task_creator: Task creation implementation
        """
        self.parser = parser
        self.persister = persister
        self.syncer = syncer
        self.task_creator = task_creator
    
    async def handle_event(self, event: Dict[str, Any], db: AsyncSession) -> None:
        """
        Main entry point for handling stream events.
        
        Pipeline:
        1. Parse event into structured data
        2. Persist brief items to database
        3. Sync detailed information
        4. Create analysis tasks
        """
        try:
            # Step 1: Parse event
            event_data = self.parser.parse(event)
            if not event_data.has_items:
                logger.debug("No items in event, skipping")
                return
            
            logger.info(f"Processing {len(event_data.items)} items from event")
            
            # Step 2: Persist brief items
            persisted_items = await self.persister.persist_brief_items(
                db, 
                event_data.items
            )
            if not persisted_items:
                logger.warning("No items were persisted")
                return
            
            logger.info(f"Persisted {len(persisted_items)} items")
            
            # Step 3: Sync details
            await self.syncer.sync_details(db, persisted_items)
            
            # Step 4: Create tasks
            await self.task_creator.create_analysis_tasks(
                db, 
                persisted_items,
                event_data.event_metadata
            )
            
            logger.info("Event processing completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to process event: {e}", exc_info=True)
            # Don't re-raise - allow system to continue


# ============================================================================
# Factory Function
# ============================================================================

def create_bilibili_event_orchestrator() -> StreamEventOrchestrator:
    """
    Factory function to create a configured Bilibili event orchestrator.
    
    This wires up all dependencies and returns a ready-to-use orchestrator.
    """
    from app.crud import crud_favorites
    from app.services import favorites_service, workshop_service
    
    return StreamEventOrchestrator(
        parser=BilibiliEventParser(),
        persister=BilibiliItemPersister(crud_favorites),
        syncer=BilibiliDetailsSyncer(favorites_service),
        task_creator=WorkshopTaskCreator(crud_favorites, workshop_service)
    )
