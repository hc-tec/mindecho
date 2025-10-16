"""
Notification Service

High-level service for triggering notifications from workshop results.
"""

from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.logging_config import get_logger
from app.crud import result as crud_result
from app.crud.crud_notification_config import crud_notification_config
from app.db.models import Workshop
from app.services.notifications.context import NotificationContext
from app.services.notifications.notifiers import LocalStorageNotifier, EmailNotifier
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
        Registers all available processors and notifiers.
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

        # Register email notifier (configuration comes from environment variables)
        try:
            register_notifier("email", EmailNotifier())
            logger.info("Email notifier registered successfully")
        except Exception as e:
            logger.warning(f"Email notifier registration failed (check SMTP env vars): {e}")

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
        Now reads configuration from database to determine notification behavior.

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

            # Load notification configuration from database
            config = await crud_notification_config.get_or_create_default(db, workshop.workshop_id)

            # Check if notifications are enabled for this workshop
            if not config.enabled:
                logger.debug(f"Notifications disabled for workshop '{workshop.workshop_id}', skipping")
                return

            # Parse configuration
            processors = json.loads(config.processors)
            notifier_type = config.notifier_type
            processor_config = json.loads(config.processor_config)

            logger.info(
                f"Sending notification for result {result_id} "
                f"(workshop: {workshop.workshop_id}, processors: {processors}, notifier: {notifier_type})"
            )

            # Create notification context
            context = NotificationContext(
                result_id=result_id,
                result_text=result_obj.content or "",
                favorite_item=result_obj.favorite_item,
                workshop=workshop,
            )

            # Apply processor configuration to dynamically configure processors
            # Note: This is a simplified implementation. For full customization,
            # we would need to instantiate processors with custom parameters.
            # For now, we use the pre-registered processors.

            # Create pipeline from database config
            pipeline = NotificationPipeline(
                name=f"config_{workshop.workshop_id}",
                processor_names=processors,
                notifier_name=notifier_type,
            )

            # Execute pipeline
            result = await pipeline.execute(context, db)

            if result.is_success:
                logger.info(
                    f"Notification sent successfully for result {result_id} "
                    f"via {notifier_type}"
                )
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
