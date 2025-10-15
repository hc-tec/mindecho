from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, asc, update, delete
from sqlalchemy.orm import selectinload, joinedload

from .base import CRUDBase
from app.db import models
from app.schemas.unified import (
    AuthorCreate, Author,
    CollectionCreate,
    TagCreate, Tag,
    FavoriteItemCreate, FavoriteItem as FavoriteItemSchema
)
from app.db.models import item_tags


class CRUDAuthor(CRUDBase[models.Author, AuthorCreate, Author]):
    async def get_by_platform_id(self, db: AsyncSession, *, platform: models.PlatformEnum, platform_user_id: str) -> \
    Optional[models.Author]:
        result = await db.execute(
            select(self.model)
            .filter(self.model.platform == platform, self.model.platform_user_id == platform_user_id)
        )
        return result.scalars().first()


class CRUDCollection(CRUDBase[models.Collection, CollectionCreate, models.Collection]):
    async def get_by_platform_id(self, db: AsyncSession, *, platform: models.PlatformEnum,
                                 platform_collection_id: str) -> Optional[models.Collection]:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.author))
            .filter(self.model.platform == platform, self.model.platform_collection_id == platform_collection_id)
        )
        return result.scalars().first()

    async def get_with_author(self, db: AsyncSession, *, id: int) -> Optional[models.Collection]:
        result = await db.execute(
            select(self.model).options(selectinload(self.model.author)).filter(self.model.id == id)
        )
        return result.scalars().first()


class CRUDTag(CRUDBase[models.Tag, TagCreate, Tag]):
    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[models.Tag]:
        result = await db.execute(select(self.model).filter(self.model.name == name))
        return result.scalars().first()

    async def get_or_create_many(self, db: AsyncSession, *, tag_names: List[str]) -> List[models.Tag]:
        tags = []
        for raw in tag_names:
            # Normalize tag input: allow dicts or strings
            if isinstance(raw, dict):
                normalized = raw.get("tag_name") or raw.get("name") or raw.get("title") or str(raw)
            else:
                normalized = str(raw)
            normalized = normalized.strip()
            if not normalized:
                continue
            tag = await self.get_by_name(db, name=normalized)
            if not tag:
                tag = await self.create(db, obj_in=TagCreate(name=normalized))
            tags.append(tag)
        return tags

    async def get_with_counts(self, db: AsyncSession) -> List[Dict[str, Any]]:
        query = (
            select(
                self.model.name,
                func.count(item_tags.c.item_id).label("count")
            )
            .join(item_tags, self.model.id == item_tags.c.tag_id)
            .group_by(self.model.name)
            .order_by(desc("count"))
        )
        result = await db.execute(query)
        return [{"name": row.name, "count": row.count} for row in result.all()]


class CRUDFavoriteItem(CRUDBase[models.FavoriteItem, FavoriteItemCreate, FavoriteItemSchema]):
    def _apply_full_load_options(self, query):
        """Helper to apply all necessary eager loading options for a favorite item."""
        return query.options(
            selectinload(self.model.author),
            selectinload(self.model.collection).selectinload(models.Collection.author),
            selectinload(self.model.tags),
            selectinload(self.model.results),
            selectinload(self.model.bilibili_video_details).options(
                selectinload(models.BilibiliVideoDetail.video_url),
                selectinload(models.BilibiliVideoDetail.audio_url),
                selectinload(models.BilibiliVideoDetail.subtitles),
            ),
            selectinload(self.model.xiaohongshu_note_details).options(
                selectinload(models.XiaohongshuNoteDetail.images),
                selectinload(models.XiaohongshuNoteDetail.video),
            ),
        )

    async def get_full(self, db: AsyncSession, *, id: int) -> Optional[models.FavoriteItem]:
        query = self._apply_full_load_options(select(self.model).filter(self.model.id == id))
        result = await db.execute(query)
        return result.scalars().unique().first()

    async def update_status_bulk(self, db: AsyncSession, *, ids: List[int], status: models.FavoriteItemStatus) -> int:
        """Updates the status for multiple favorite items in a single operation."""
        if not ids:
            return 0

        stmt = (
            update(self.model)
            .where(self.model.id.in_(ids))
            .values(status=status)
            .execution_options(synchronize_session=False)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def remove_bulk(self, db: AsyncSession, *, ids: List[int]) -> int:
        """Deletes multiple favorite items in a single operation."""
        if not ids:
            return 0

        # We might need to handle related objects manually if cascading deletes are not set up
        # For now, let's assume cascading is handled or not needed for this operation.

        # First, delete the associations in the item_tags table
        await db.execute(delete(item_tags).where(item_tags.c.item_id.in_(ids)))

        # Then, delete the items themselves
        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = await db.execute(stmt)

        await db.commit()
        return result.rowcount

    async def get_by_platform_item_id(self, db: AsyncSession, *, platform_item_id: str) -> Optional[
        models.FavoriteItem]:
        query = self._apply_full_load_options(
            select(self.model).filter(self.model.platform_item_id == platform_item_id)
        )
        result = await db.execute(query)
        return result.scalars().unique().first()

    async def get_by_platform_item_id_with_details(self, db: AsyncSession, *, platform_item_id: str) -> Optional[
        models.FavoriteItem]:
        """Gets a single favorite item by its platform ID with all relations pre-loaded."""
        query = select(self.model).filter(self.model.platform_item_id == platform_item_id)
        query = self._apply_full_load_options(query)
        result = await db.execute(query)
        return result.scalars().unique().first()

    async def create_brief_with_relationships(
            self,
            db: AsyncSession,
            *,
            item_in: FavoriteItemCreate,
            author_id: int,
            collection_id: Optional[str] = None,
    ) -> models.FavoriteItem:
        """Create a FavoriteItem (brief) while assigning author_id and optional collection_id.

        This is intended for ingestion of plugin stream events where we only have brief info.

        Args:
            collection_id: Platform collection ID (foreign key to collections.platform_collection_id)
        """
        db_item = models.FavoriteItem(
            **item_in.dict(),
            author_id=author_id,
            collection_id=collection_id,
        )
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item)
        return db_item

    async def get_multi_paginated_with_filters(
            self,
            db: AsyncSession,
            *,
            skip: int = 0,
            limit: int = 20,
            sort_by: str = "favorited_at",
            sort_order: str = "desc",
            tags: Optional[List[str]] = None,
    ) -> Tuple[List[models.FavoriteItem], int]:

        query = select(self.model)  # Base query

        if tags:
            for tag_name in tags:
                query = query.where(self.model.tags.any(models.Tag.name == tag_name))

        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        query_with_loads = self._apply_full_load_options(query)

        sort_column = getattr(self.model, sort_by, self.model.favorited_at)
        if sort_order == "desc":
            query_with_loads = query_with_loads.order_by(desc(sort_column))
        else:
            query_with_loads = query_with_loads.order_by(asc(sort_column))

        query_with_loads = query_with_loads.offset(skip).limit(limit)

        items_result = await db.execute(query_with_loads)
        items = items_result.scalars().unique().all()

        return items, total

    async def get_multi_inbox(
            self,
            db: AsyncSession,
            *,
            skip: int = 0,
            limit: int = 20,
            sort_by: str = "favorited_at",
            sort_order: str = "desc",
    ) -> Tuple[List[models.FavoriteItem], int]:

        base_query = select(self.model).where(self.model.status == models.FavoriteItemStatus.PENDING)

        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        query = self._apply_full_load_options(base_query)

        sort_column = getattr(self.model, sort_by, self.model.favorited_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        query = query.offset(skip).limit(limit)

        items_result = await db.execute(query)
        items = items_result.scalars().unique().all()

        return items, total

    async def add_tags(self, db: AsyncSession, *, item_id: int, tag_names: List[str]) -> bool:
        db_item = await self.get_full(db, id=item_id)
        if not db_item:
            return False

        tags_to_add = await tag.get_or_create_many(db, tag_names=tag_names)
        existing_tag_names = {t.name for t in db_item.tags}

        for t in tags_to_add:
            if t.name not in existing_tag_names:
                db_item.tags.append(t)

        await db.commit()
        return True

    async def remove_tags(self, db: AsyncSession, *, item_id: int, tag_names: List[str]) -> bool:
        db_item = await self.get_full(db, id=item_id)
        if not db_item:
            return False

        tags_to_remove_set = set(tag_names)
        db_item.tags = [t for t in db_item.tags if t.name not in tags_to_remove_set]

        await db.commit()
        return True


author = CRUDAuthor(models.Author)
collection = CRUDCollection(models.Collection)
tag = CRUDTag(models.Tag)
favorite_item = CRUDFavoriteItem(models.FavoriteItem)


