"""
API endpoints for workshop notification configuration.

Provides REST API for managing per-workshop notification settings.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api import deps
from app.crud.crud_notification_config import crud_notification_config
from app.schemas.notification_config import (
    WorkshopNotificationConfigCreate,
    WorkshopNotificationConfigUpdate,
    WorkshopNotificationConfigResponse,
    ProcessorConfigSchema,
)


router = APIRouter()


@router.get("", response_model=List[WorkshopNotificationConfigResponse])
async def list_notification_configs(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Get all workshop notification configurations.

    Returns:
        List of notification configs with their settings
    """
    configs = await crud_notification_config.get_multi(db, skip=skip, limit=limit)
    return [WorkshopNotificationConfigResponse.from_orm_model(c) for c in configs]


@router.get("/enabled", response_model=List[WorkshopNotificationConfigResponse])
async def list_enabled_configs(
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Get all enabled notification configurations.

    Useful for determining which workshops will send notifications.

    Returns:
        List of enabled notification configs
    """
    configs = await crud_notification_config.get_enabled_configs(db)
    return [WorkshopNotificationConfigResponse.from_orm_model(c) for c in configs]


@router.get("/{workshop_id}", response_model=WorkshopNotificationConfigResponse)
async def get_notification_config(
    workshop_id: str,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Get notification config for a specific workshop.

    If config doesn't exist, creates one with default settings.

    Args:
        workshop_id: Workshop identifier

    Returns:
        Notification config for the workshop
    """
    config = await crud_notification_config.get_or_create_default(db, workshop_id)
    await db.commit()
    return WorkshopNotificationConfigResponse.from_orm_model(config)


@router.post("", response_model=WorkshopNotificationConfigResponse, status_code=201)
async def create_notification_config(
    config_in: WorkshopNotificationConfigCreate,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Create notification config for a workshop.

    Args:
        config_in: Notification configuration data

    Returns:
        Created config

    Raises:
        HTTPException 400: If workshop already has a config
    """
    # Check if config already exists
    existing = await crud_notification_config.get_by_workshop_id(db, config_in.workshop_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Notification config for workshop '{config_in.workshop_id}' already exists. Use PUT to update.",
        )

    config = await crud_notification_config.create(db, config_in)
    await db.commit()
    return WorkshopNotificationConfigResponse.from_orm_model(config)


@router.put("/{workshop_id}", response_model=WorkshopNotificationConfigResponse)
async def update_notification_config(
    workshop_id: str,
    config_in: WorkshopNotificationConfigUpdate,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Update notification config for a workshop.

    Args:
        workshop_id: Workshop identifier
        config_in: Updated configuration data

    Returns:
        Updated config

    Raises:
        HTTPException 404: If config doesn't exist
    """
    config = await crud_notification_config.get_by_workshop_id(db, workshop_id)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Notification config for workshop '{workshop_id}' not found. Use POST to create.",
        )

    updated_config = await crud_notification_config.update(db, config, config_in)
    await db.commit()
    return WorkshopNotificationConfigResponse.from_orm_model(updated_config)


@router.put("/{workshop_id}/upsert", response_model=WorkshopNotificationConfigResponse)
async def upsert_notification_config(
    workshop_id: str,
    config_in: WorkshopNotificationConfigCreate,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Create or update notification config (upsert operation).

    Convenience endpoint that handles both create and update in one call.

    Args:
        workshop_id: Workshop identifier (must match config_in.workshop_id)
        config_in: Configuration data

    Returns:
        Created or updated config

    Raises:
        HTTPException 400: If workshop_id mismatch
    """
    if config_in.workshop_id != workshop_id:
        raise HTTPException(
            status_code=400,
            detail=f"workshop_id in path ({workshop_id}) must match workshop_id in body ({config_in.workshop_id})",
        )

    config = await crud_notification_config.create_or_update(db, config_in)
    await db.commit()
    return WorkshopNotificationConfigResponse.from_orm_model(config)


@router.delete("/{workshop_id}")
async def delete_notification_config(
    workshop_id: str,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Delete notification config for a workshop.

    After deletion, the workshop will use default notification settings.

    Args:
        workshop_id: Workshop identifier

    Returns:
        Success response

    Raises:
        HTTPException 404: If config doesn't exist
    """
    deleted = await crud_notification_config.delete(db, workshop_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Notification config for workshop '{workshop_id}' not found.",
        )

    await db.commit()
    return {"ok": True, "message": f"Notification config for '{workshop_id}' deleted."}


@router.post("/{workshop_id}/toggle", response_model=WorkshopNotificationConfigResponse)
async def toggle_notifications(
    workshop_id: str,
    enabled: bool,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Quick toggle to enable/disable notifications for a workshop.

    Creates config with defaults if doesn't exist.

    Args:
        workshop_id: Workshop identifier
        enabled: True to enable, False to disable

    Returns:
        Updated config

    Query params:
        ?enabled=true  or  ?enabled=false
    """
    config = await crud_notification_config.get_or_create_default(db, workshop_id)

    update_data = WorkshopNotificationConfigUpdate(enabled=enabled)
    updated_config = await crud_notification_config.update(db, config, update_data)

    await db.commit()
    return WorkshopNotificationConfigResponse.from_orm_model(updated_config)


@router.get("/{workshop_id}/defaults", response_model=WorkshopNotificationConfigResponse)
async def get_default_config(
    workshop_id: str,
):
    """
    Get default notification config structure (without saving to database).

    Useful for UI to show default values.

    Args:
        workshop_id: Workshop identifier

    Returns:
        Default config structure
    """
    from app.db.models import WorkshopNotificationConfig
    import json

    # Create in-memory default config
    default_config = WorkshopNotificationConfig(
        id=0,
        workshop_id=workshop_id,
        enabled=1,
        processors='["text_formatter"]',
        notifier_type="local_storage",
        processor_config=json.dumps(ProcessorConfigSchema().model_dump()),
        notifier_config="{}",
    )

    return WorkshopNotificationConfigResponse.from_orm_model(default_config)
