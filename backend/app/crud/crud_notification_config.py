"""
CRUD operations for workshop notification configuration.

Provides database access layer for notification config management.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
import json
import datetime

from app.db.models import WorkshopNotificationConfig
from app.schemas.notification_config import (
    WorkshopNotificationConfigCreate,
    WorkshopNotificationConfigUpdate,
    ProcessorConfigSchema,
)


class CRUDNotificationConfig:
    """CRUD operations for WorkshopNotificationConfig."""

    async def get_by_workshop_id(
        self,
        db: AsyncSession,
        workshop_id: str,
    ) -> Optional[WorkshopNotificationConfig]:
        """Get notification config for a specific workshop."""
        stmt = select(WorkshopNotificationConfig).where(
            WorkshopNotificationConfig.workshop_id == workshop_id
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> List[WorkshopNotificationConfig]:
        """Get multiple notification configs."""
        stmt = select(WorkshopNotificationConfig).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_enabled_configs(
        self,
        db: AsyncSession,
    ) -> List[WorkshopNotificationConfig]:
        """Get all enabled notification configs."""
        stmt = select(WorkshopNotificationConfig).where(
            WorkshopNotificationConfig.enabled == 1
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        db: AsyncSession,
        obj_in: WorkshopNotificationConfigCreate,
    ) -> WorkshopNotificationConfig:
        """
        Create new notification config.

        Args:
            db: Database session
            obj_in: Config data from request

        Returns:
            Created config object

        Raises:
            IntegrityError if workshop_id already has a config
        """
        # Serialize JSON fields
        processors_json = json.dumps(obj_in.processors)
        processor_config_json = json.dumps(obj_in.processor_config.model_dump())
        notifier_config_json = json.dumps(obj_in.notifier_config)

        db_obj = WorkshopNotificationConfig(
            workshop_id=obj_in.workshop_id,
            enabled=1 if obj_in.enabled else 0,
            processors=processors_json,
            notifier_type=obj_in.notifier_type,
            processor_config=processor_config_json,
            notifier_config=notifier_config_json,
        )

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: WorkshopNotificationConfig,
        obj_in: WorkshopNotificationConfigUpdate,
    ) -> WorkshopNotificationConfig:
        """
        Update existing notification config.

        Args:
            db: Database session
            db_obj: Existing config object
            obj_in: Update data from request

        Returns:
            Updated config object
        """
        # Update fields if provided
        if obj_in.enabled is not None:
            db_obj.enabled = 1 if obj_in.enabled else 0

        if obj_in.processors is not None:
            db_obj.processors = json.dumps(obj_in.processors)

        if obj_in.notifier_type is not None:
            db_obj.notifier_type = obj_in.notifier_type

        if obj_in.processor_config is not None:
            db_obj.processor_config = json.dumps(obj_in.processor_config.model_dump())

        if obj_in.notifier_config is not None:
            db_obj.notifier_config = json.dumps(obj_in.notifier_config)

        # Update timestamp
        db_obj.updated_at = datetime.datetime.utcnow()

        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def delete(
        self,
        db: AsyncSession,
        workshop_id: str,
    ) -> bool:
        """
        Delete notification config for a workshop.

        Args:
            db: Database session
            workshop_id: Workshop ID

        Returns:
            True if deleted, False if not found
        """
        db_obj = await self.get_by_workshop_id(db, workshop_id)
        if db_obj:
            await db.delete(db_obj)
            await db.flush()
            return True
        return False

    async def create_or_update(
        self,
        db: AsyncSession,
        obj_in: WorkshopNotificationConfigCreate,
    ) -> WorkshopNotificationConfig:
        """
        Create config if doesn't exist, otherwise update.

        Convenience method for upsert operations.

        Args:
            db: Database session
            obj_in: Config data

        Returns:
            Created or updated config object
        """
        existing = await self.get_by_workshop_id(db, obj_in.workshop_id)
        if existing:
            # Convert create schema to update schema
            update_data = WorkshopNotificationConfigUpdate(
                enabled=obj_in.enabled,
                processors=obj_in.processors,
                notifier_type=obj_in.notifier_type,
                processor_config=obj_in.processor_config,
                notifier_config=obj_in.notifier_config,
            )
            return await self.update(db, existing, update_data)
        else:
            return await self.create(db, obj_in)

    async def get_or_create_default(
        self,
        db: AsyncSession,
        workshop_id: str,
    ) -> WorkshopNotificationConfig:
        """
        Get config for workshop, or create with default settings.

        Ensures every workshop has a notification config.

        Args:
            db: Database session
            workshop_id: Workshop ID

        Returns:
            Existing or newly created config
        """
        existing = await self.get_by_workshop_id(db, workshop_id)
        if existing:
            return existing

        # Create default config
        default_config = WorkshopNotificationConfigCreate(
            workshop_id=workshop_id,
            enabled=True,
            processors=["text_formatter"],
            notifier_type="local_storage",
            processor_config=ProcessorConfigSchema(),
            notifier_config={},
        )
        return await self.create(db, default_config)


# Singleton instance
crud_notification_config = CRUDNotificationConfig()
