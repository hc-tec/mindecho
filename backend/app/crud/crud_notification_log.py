"""
CRUD operations for NotificationLog model.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NotificationLog, NotificationStatus


class CRUDNotificationLog:
    """CRUD operations for notification logs."""

    async def create(
        self,
        db: AsyncSession,
        *,
        result_id: int,
        pipeline_name: str,
        notifier_type: str,
        status: NotificationStatus = NotificationStatus.PENDING,
        content_snapshot: Optional[str] = None,
        error_message: Optional[str] = None,
        external_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NotificationLog:
        """
        Create a new notification log entry.

        Args:
            db: Database session
            result_id: ID of the Result that triggered notification
            pipeline_name: Name of the pipeline that ran
            notifier_type: Type of notifier used
            status: Delivery status
            content_snapshot: Truncated content for debugging
            error_message: Error message if failed
            external_id: External platform ID
            metadata: Additional metadata

        Returns:
            Created NotificationLog instance
        """
        metadata_json = json.dumps(metadata or {})

        log = NotificationLog(
            result_id=result_id,
            pipeline_name=pipeline_name,
            notifier_type=notifier_type,
            status=status,
            content_snapshot=content_snapshot,
            error_message=error_message,
            external_id=external_id,
            metadata=metadata_json,
        )

        db.add(log)
        await db.flush()
        await db.refresh(log)

        return log

    async def update_status(
        self,
        db: AsyncSession,
        log_id: int,
        status: NotificationStatus,
        error_message: Optional[str] = None,
        external_id: Optional[str] = None,
        sent_at: Optional[datetime] = None,
    ) -> Optional[NotificationLog]:
        """
        Update the status of a notification log.

        Args:
            db: Database session
            log_id: ID of the log to update
            status: New status
            error_message: Error message if failed
            external_id: External platform ID if successful
            sent_at: Timestamp when sent (defaults to now if status is SUCCESS)

        Returns:
            Updated NotificationLog or None if not found
        """
        result = await db.execute(select(NotificationLog).where(NotificationLog.id == log_id))
        log = result.scalars().first()

        if not log:
            return None

        log.status = status
        if error_message:
            log.error_message = error_message
        if external_id:
            log.external_id = external_id

        # Auto-set sent_at if status is SUCCESS and sent_at not provided
        if status == NotificationStatus.SUCCESS:
            log.sent_at = sent_at or datetime.utcnow()

        await db.flush()
        await db.refresh(log)

        return log

    async def increment_retry(
        self, db: AsyncSession, log_id: int
    ) -> Optional[NotificationLog]:
        """
        Increment retry count for a notification log.

        Args:
            db: Database session
            log_id: ID of the log to update

        Returns:
            Updated NotificationLog or None if not found
        """
        result = await db.execute(select(NotificationLog).where(NotificationLog.id == log_id))
        log = result.scalars().first()

        if not log:
            return None

        log.retry_count += 1
        log.status = NotificationStatus.RETRYING

        await db.flush()
        await db.refresh(log)

        return log

    async def get_by_id(self, db: AsyncSession, log_id: int) -> Optional[NotificationLog]:
        """Get a notification log by ID."""
        result = await db.execute(select(NotificationLog).where(NotificationLog.id == log_id))
        return result.scalars().first()

    async def get_by_result_id(
        self, db: AsyncSession, result_id: int
    ) -> List[NotificationLog]:
        """
        Get all notification logs for a specific result.

        Args:
            db: Database session
            result_id: ID of the Result

        Returns:
            List of NotificationLog instances
        """
        result = await db.execute(
            select(NotificationLog)
            .where(NotificationLog.result_id == result_id)
            .order_by(NotificationLog.created_at.desc())
        )
        return result.scalars().all()

    async def get_pending_retries(
        self, db: AsyncSession, max_retries: int = 3
    ) -> List[NotificationLog]:
        """
        Get notification logs that are pending retry.

        Args:
            db: Database session
            max_retries: Maximum number of retries allowed

        Returns:
            List of NotificationLog instances eligible for retry
        """
        result = await db.execute(
            select(NotificationLog)
            .where(
                NotificationLog.status.in_(
                    [NotificationStatus.PENDING, NotificationStatus.RETRYING]
                ),
                NotificationLog.retry_count < max_retries,
            )
            .order_by(NotificationLog.created_at.asc())
        )
        return result.scalars().all()

    async def get_failed_logs(
        self, db: AsyncSession, limit: int = 100
    ) -> List[NotificationLog]:
        """
        Get recent failed notification logs.

        Args:
            db: Database session
            limit: Maximum number of logs to return

        Returns:
            List of failed NotificationLog instances
        """
        result = await db.execute(
            select(NotificationLog)
            .where(NotificationLog.status == NotificationStatus.FAILED)
            .order_by(NotificationLog.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()


# Global instance
notification_log = CRUDNotificationLog()
