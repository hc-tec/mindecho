"""
Notification Service

High-level service for triggering notifications from workshop results.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.crud import result as crud_result
from app.db.models import Workshop
from app.services.notifications.context import NotificationContext
from app.services.notifications.notifiers import LocalStorageNotifier
from app.services.notifications.pipeline import NotificationPipeline, PipelineOrchestrator
from app.services.notifications.processors import ImageRendererProcessor, TextFormatterProcessor
from app.services.notifications.registry import register_notifier, register_processor

logger = get_logger(__name__)


class NotificationService:
    """
    Main service for notification system.

    Handles registration of default plugins and triggering notifications.
    """

    _initialized = False

    @classmethod
    def initialize(cls):
        """
        Initialize notification system with default plugins.

        This should be called once during application startup.
        """
        if cls._initialized:
            return

        logger.info("Initializing notification system...")

        # Register default processors
        register_processor("text_formatter", TextFormatterProcessor())
        register_processor(
            "text_formatter_plain",
            TextFormatterProcessor(output_format="plain", max_length=500),
        )
        register_processor("image_renderer", ImageRendererProcessor())

        # Register default notifiers
        register_notifier("local_storage", LocalStorageNotifier())

        cls._initialized = True
        logger.info("Notification system initialized successfully")

    @classmethod
    async def notify_result_created(
        cls,
        db: AsyncSession,
        result_id: int,
        workshop: Workshop,
    ) -> None:
        """
        Trigger notifications for a newly created workshop result.

        This is the main entry point called by WorkshopService when using an existing session.

        Args:
            db: Database session
            result_id: ID of the created Result
            workshop: Workshop that generated the result
        """
        if not cls._initialized:
            logger.warning("Notification system not initialized, skipping notification")
            return

        try:
            # Fetch the result with all relationships
            result_obj = await crud_result.get_with_item(db, result_id=result_id)
            if not result_obj:
                logger.error(f"Result {result_id} not found, cannot send notification")
                return

            if not result_obj.favorite_item:
                logger.error(f"Result {result_id} has no favorite_item, cannot send notification")
                return

            # Create notification context
            context = NotificationContext(
                result_id=result_id,
                result_text=result_obj.content or "",
                favorite_item=result_obj.favorite_item,
                workshop=workshop,
            )

            # Create default pipeline (MVP: text formatter + local storage)
            pipeline = NotificationPipeline(
                name="default_local",
                processor_names=["text_formatter"],
                notifier_name="local_storage",
            )

            # Execute pipeline
            result = await pipeline.execute(context, db)

            if result.is_success:
                logger.info(f"Notification sent successfully for result {result_id}")
            else:
                logger.warning(
                    f"Notification failed for result {result_id}: {result.error_message}"
                )

        except Exception as e:
            logger.error(f"Failed to send notification for result {result_id}: {e}", exc_info=True)
            # Don't re-raise - notification failure shouldn't break workshop execution

    @classmethod
    async def notify_result_created_async(
        cls,
        result_id: int,
        workshop: Workshop,
    ) -> None:
        """
        Trigger notifications for a newly created workshop result (async version).

        This version creates its own database session and is safe to call from background tasks.

        Args:
            result_id: ID of the created Result
            workshop: Workshop that generated the result
        """
        from app.db.base import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await cls.notify_result_created(db, result_id, workshop)


# Global service instance
notification_service = NotificationService()
