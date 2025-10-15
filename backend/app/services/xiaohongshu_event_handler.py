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
    """Brief note information from Xiaohongshu stream event.

    Matches RPC NoteBriefItem structure - does NOT include collection_id
    because RPC doesn't return it.
    """
    note_id: str
    xsec_token: str
    title: str
    cover_image: str
    creator: XiaohongshuCreatorInfo
    fav_time: str
    statistic: Optional[Dict[str, Any]] = None


@dataclass
class XiaohongshuStreamEventData:
    """Parsed Xiaohongshu stream event data."""
    items: List[XiaohongshuNoteItemBrief]
    collection_id: str  # Extracted from event params, not from items!
    event_metadata: Dict[str, Any]


@dataclass
class PersistResult:
    """Result of item persistence operation.

    Distinguishes between newly created items and existing items that need recovery.
    """
    newly_created: List[models.FavoriteItem]  # Items created in this operation
    needs_recovery: List[models.FavoriteItem]  # Existing items with incomplete processing

    @property
    def all_items(self) -> List[models.FavoriteItem]:
        """All items that need processing (new + recovery)."""
        return self.newly_created + self.needs_recovery

    @property
    def total_count(self) -> int:
        """Total number of items."""
        return len(self.newly_created) + len(self.needs_recovery)


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
        self,
        db: AsyncSession,
        items: List[XiaohongshuNoteItemBrief],
        collection_id: str
    ) -> PersistResult:
        """Persist brief items, distinguishing new vs existing items needing recovery.

        Args:
            collection_id: Platform collection ID (from event params, not from items)

        Returns:
            PersistResult with newly_created and needs_recovery lists
        """
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
        """Parse Xiaohongshu event structure.

        CRITICAL: RPC NoteBriefItem does NOT contain collection_id.
        We extract collection_id from event params (injected by stream_manager).
        """
        # Extract collection_id from event params (NOT from RPC items!)
        params = event.get("params") or {}
        collection_id = str(params.get("collection_id", ""))

        if not collection_id:
            logger.error(f"Event missing collection_id in params! Cannot associate notes with collection.")

        payload = event.get("payload") or {}
        result = payload.get("result") if isinstance(payload, dict) else None

        if not isinstance(result, dict) or not result.get("success"):
            return XiaohongshuStreamEventData(
                items=[],
                collection_id=collection_id,
                event_metadata=event
            )

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
                    # NO collection_id here! RPC doesn't return it!
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

        return XiaohongshuStreamEventData(
            items=notes,
            collection_id=collection_id,
            event_metadata=event
        )


class DefaultXiaohongshuItemPersister:
    """Default persister for Xiaohongshu note brief items."""

    async def persist_brief_items(
        self,
        db: AsyncSession,
        items: List[XiaohongshuNoteItemBrief],
        collection_id: str
    ) -> PersistResult:
        """Idempotently persist brief note items with recovery detection.

        Args:
            collection_id: Platform collection ID (from stream params, not from RPC items)

        Returns:
            PersistResult distinguishing newly created vs items needing recovery
        """
        newly_created = []
        needs_recovery = []

        for note in items:
            try:
                # Check if already exists
                existing = await crud_favorites.favorite_item.get_by_platform_item_id(
                    db, platform_item_id=note.note_id
                )
                if existing:
                    # Check if this existing item needs recovery (incomplete processing)
                    if await self._needs_recovery(db, existing):
                        logger.info(
                            f"Note {note.note_id} exists but needs recovery "
                            f"(incomplete details or task)"
                        )
                        needs_recovery.append(existing)
                    else:
                        logger.debug(f"Note {note.note_id} already fully processed, skipping")
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

                # Verify collection exists in DB (optional, for FK integrity)
                db_collection = None
                if collection_id:
                    db_collection = await crud_favorites.collection.get_by_platform_id(
                        db,
                        platform=models.PlatformEnum.xiaohongshu,
                        platform_collection_id=collection_id
                    )
                    if not db_collection:
                        logger.warning(
                            f"Collection {collection_id} not found in DB for note {note.note_id}. "
                            f"FK constraint may fail if collection hasn't been synced yet!"
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
                    collection_id=collection_id  # Use collection_id from persister parameter!
                )
                logger.info(f"Created FavoriteItem for note {note.note_id}, collection_id: {db_item.collection_id}")

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

                newly_created.append(db_item)

            except Exception as e:
                logger.exception(f"Failed to persist Xiaohongshu note {note.note_id}: {e}")
                continue

        return PersistResult(
            newly_created=newly_created,
            needs_recovery=needs_recovery
        )

    async def _needs_recovery(self, db: AsyncSession, item: models.FavoriteItem) -> bool:
        """检查已存在的内容项是否需要恢复处理（未完成的处理流程）

        内容项需要恢复的场景：
        1. 缺少详情数据（且重试次数未耗尽 或 距上次尝试超过24小时）
        2. 已有详情但完全没有任务（无论成功或未完成的任务）

        Args:
            db: 数据库会话
            item: 待检查的收藏项

        Returns:
            True 表示需要恢复处理，False 表示已完整处理无需恢复
        """
        from app.crud import crud_tasks
        from sqlalchemy import select

        # === 检查1：是否缺少详情数据（且未耗尽重试次数）===
        has_details = (
            item.xiaohongshu_note_details  # 详情对象存在
            and item.xiaohongshu_note_details.desc  # 且描述不为空
        )

        if not has_details:
            # 如果详情缺失，检查是否还有重试机会
            max_attempts = 5  # 最大重试次数（TODO: 从配置读取）

            # 情况1：重试次数未达上限，允许恢复
            if (item.details_fetch_attempts or 0) < max_attempts:
                return True

            # 情况2：距离上次尝试超过24小时，给予新的机会
            if item.details_last_attempt_at:
                hours_since_attempt = (
                    datetime.datetime.utcnow() - item.details_last_attempt_at
                ).total_seconds() / 3600
                if hours_since_attempt > 24:
                    return True

            # 重试次数已耗尽且未过24小时，放弃恢复
            return False

        # === 检查2：是否缺少任务（检查ANY状态的任务，不仅仅是未完成的）===
        # ⚠️ 关键修复：如果item已经有SUCCESS状态的task，说明已完整处理，无需恢复！
        any_task = await db.execute(
            select(models.Task).where(
                models.Task.favorite_item_id == item.id
            ).limit(1)
        )
        has_any_task = any_task.scalars().first() is not None

        # 只有当item有详情但完全没有任何task时，才需要恢复
        return not has_any_task


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
        """为具有完整详情的内容项创建workshop分析任务

        只为满足以下条件的item创建任务：
        1. 已成功获取详情数据
        2. 不存在任何task（无论成功、失败还是进行中）

        Args:
            db: 数据库会话
            items: 待处理的收藏项列表
            event_metadata: Stream事件元数据，用于解析workshop ID
        """
        from app.crud import crud_tasks
        from sqlalchemy import select

        for db_item in items:
            try:
                # === 前置检查1：验证详情数据是否存在 ===
                if not db_item.xiaohongshu_note_details or not db_item.xiaohongshu_note_details.desc:
                    logger.info(
                        f"跳过任务创建 - 笔记 {db_item.platform_item_id}：详情数据不可用"
                    )
                    continue

                # === 前置检查2：检查是否已存在任何任务（防止重复创建）===
                # ⚠️ 关键修复：检查ANY状态的task，不仅仅是未完成的！
                # 如果item已经有SUCCESS task，绝不能创建重复任务！
                any_task = await db.execute(
                    select(models.Task).where(
                        models.Task.favorite_item_id == db_item.id
                    ).limit(1)
                )
                existing_task = any_task.scalars().first()

                if existing_task:
                    logger.info(
                        f"跳过任务创建 - 笔记 {db_item.platform_item_id}：已存在任务 {existing_task.id} "
                        f"(状态: {existing_task.status})"
                    )
                    continue

                # Resolve workshop_id from collection or default
                workshop_id = await self._resolve_workshop_id(db, db_item, event_metadata)

                # Create workshop task
                task = await workshop_service.start_workshop_task(
                    db, workshop_id=workshop_id, collection_id=db_item.id
                )

                # Run task in background (creates its own DB session)
                asyncio.create_task(workshop_service.run_workshop_task(task_id=task.id))

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
                collection = await crud_favorites.collection.get_by_platform_id(
                    db,
                    platform=models.PlatformEnum.xiaohongshu,
                    platform_collection_id=db_item.collection_id
                )
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
        task_creator: XiaohongshuTaskCreator,
        first_sync_threshold: Optional[int] = None
    ):
        self.parser = parser
        self.persister = persister
        self.syncer = syncer
        self.task_creator = task_creator
        self.first_sync_threshold = first_sync_threshold or settings.FIRST_SYNC_THRESHOLD

    async def handle_event(self, event: Dict[str, Any], db: AsyncSession) -> None:
        """
        Handle Xiaohongshu stream event with ordered pipeline:
        1. Parse event (extracts collection_id from params)
        2. Persist brief items (pass collection_id to persister)
        3. Check for first sync (skip AI processing if threshold exceeded)
        4. Sync details (with retry support + recovery)
        5. Create tasks (only for items with details)
        """
        logger.info("Processing Xiaohongshu stream event")

        # Step 1: Parse
        event_data = await self.parser.parse(event)
        if not event_data.items:
            logger.info("No items to process in event")
            return

        logger.info(
            f"Parsed {len(event_data.items)} Xiaohongshu notes from event "
            f"(collection_id: {event_data.collection_id})"
        )

        # Step 2: Persist brief items (with recovery detection)
        persist_result = await self.persister.persist_brief_items(
            db,
            event_data.items,
            event_data.collection_id
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
        if await self._is_first_sync(persist_result):
            logger.warning(
                f"⚠️  First sync detected: {len(persist_result.newly_created)} new items "
                f"exceeds threshold ({self.first_sync_threshold}). "
                f"Skipping AI processing to avoid overwhelming the system."
            )
            return

        # Step 4: Sync details (with retry mechanism + recovery)
        items_with_details = await self.syncer.sync_details(db, persist_result.all_items)
        logger.info(
            f"Successfully fetched details for {len(items_with_details)}/"
            f"{persist_result.total_count} notes"
        )

        # Step 5: Create tasks (only for items with details)
        if items_with_details:
            await self.task_creator.create_analysis_tasks(
                db, items_with_details, event_data.event_metadata
            )

    async def _is_first_sync(self, persist_result: PersistResult) -> bool:
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

def create_xiaohongshu_event_orchestrator(
    retry_delay_minutes: Optional[int] = None,
    max_retry_attempts: Optional[int] = None,
    first_sync_threshold: Optional[int] = None
) -> XiaohongshuStreamEventOrchestrator:
    """
    Factory to create Xiaohongshu event orchestrator with default implementations.

    Args:
        retry_delay_minutes: Minutes to wait between retry attempts (default: from config)
        max_retry_attempts: Maximum retry attempts per note (default: from config)
        first_sync_threshold: Threshold for first sync detection (default: from config)

    Returns:
        Configured orchestrator instance
    """
    return XiaohongshuStreamEventOrchestrator(
        parser=DefaultXiaohongshuEventParser(),
        persister=DefaultXiaohongshuItemPersister(),
        syncer=DefaultXiaohongshuDetailsSyncer(
            retry_delay_minutes=retry_delay_minutes or settings.XIAOHONGSHU_DETAILS_RETRY_DELAY_MINUTES,
            max_attempts=max_retry_attempts or settings.XIAOHONGSHU_DETAILS_MAX_RETRY_ATTEMPTS
        ),
        task_creator=DefaultXiaohongshuTaskCreator(),
        first_sync_threshold=first_sync_threshold
    )
