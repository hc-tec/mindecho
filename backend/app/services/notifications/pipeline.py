"""
Notification Pipeline

Orchestrates the notification process: processors → notifier → logging.
"""

from datetime import datetime
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.crud import notification_log
from app.db.models import NotificationStatus
from app.services.notifications.context import NotificationContext, NotificationResult
from app.services.notifications.protocols import ResultNotifier, ResultProcessor
from app.services.notifications.registry import get_notifier, get_processor

logger = get_logger(__name__)


class NotificationPipeline:
    """
    Orchestrates notification pipeline execution.

    Flow:
    1. Create NotificationContext from result
    2. Run processors sequentially (text_formatter → image_renderer → ...)
    3. Run notifier (email, xiaohongshu, local_storage)
    4. Save notification log to database
    """

    def __init__(
        self,
        name: str,
        processor_names: List[str],
        notifier_name: str,
    ):
        """
        Initialize notification pipeline.

        Args:
            name: Pipeline name (for identification and logging)
            processor_names: List of processor names to run in sequence
            notifier_name: Notifier name to use for sending
        """
        self.name = name
        self.processor_names = processor_names
        self.notifier_name = notifier_name

    async def execute(
        self,
        context: NotificationContext,
        db: AsyncSession,
    ) -> NotificationResult:
        """
        Execute the notification pipeline.

        Args:
            context: Notification context
            db: Database session for logging

        Returns:
            NotificationResult with success/failure status
        """
        logger.info(
            f"Executing pipeline '{self.name}' for result {context.result_id}"
        )

        try:
            # Step 1: Run processors
            for processor_name in self.processor_names:
                processor = get_processor(processor_name)
                if not processor:
                    error_msg = f"Processor '{processor_name}' not found in registry"
                    logger.warning(error_msg)
                    context.add_error(error_msg)
                    continue

                try:
                    logger.debug(f"Running processor: {processor_name}")
                    context = await processor.process(context)
                except Exception as e:
                    error_msg = f"Processor '{processor_name}' failed: {e}"
                    logger.error(error_msg, exc_info=True)
                    context.add_error(error_msg)
                    # Continue with next processor

            # Step 2: Run notifier
            notifier = get_notifier(self.notifier_name)
            if not notifier:
                error_msg = f"Notifier '{self.notifier_name}' not found in registry"
                logger.error(error_msg)
                result = NotificationResult(
                    status=NotificationStatus.FAILED,
                    notifier_type=self.notifier_name,
                    sent_at=datetime.utcnow(),
                    error_message=error_msg,
                )
            else:
                logger.debug(f"Running notifier: {self.notifier_name}")
                result = await notifier.send(context)

            # Step 3: Save notification log
            await self._save_log(db, context, result)

            if result.is_success:
                logger.info(
                    f"Pipeline '{self.name}' completed successfully "
                    f"(result_id={context.result_id})"
                )
            else:
                logger.warning(
                    f"Pipeline '{self.name}' failed: {result.error_message} "
                    f"(result_id={context.result_id})"
                )

            return result

        except Exception as e:
            error_msg = f"Pipeline execution failed: {e}"
            logger.error(error_msg, exc_info=True)

            # Create failure result
            result = NotificationResult(
                status=NotificationStatus.FAILED,
                notifier_type=self.notifier_name,
                sent_at=datetime.utcnow(),
                error_message=error_msg,
            )

            # Try to save log even on failure
            try:
                await self._save_log(db, context, result)
            except Exception as log_error:
                logger.error(f"Failed to save error log: {log_error}")

            return result

    async def _save_log(
        self,
        db: AsyncSession,
        context: NotificationContext,
        result: NotificationResult,
    ) -> None:
        """Save notification log to database."""
        try:
            # Truncate content for snapshot (max 1000 chars)
            content_snapshot = context.get_display_text()[:1000]

            await notification_log.create(
                db,
                result_id=context.result_id,
                pipeline_name=self.name,
                notifier_type=result.notifier_type,
                status=result.status,
                content_snapshot=content_snapshot,
                error_message=result.error_message,
                external_id=result.external_id,
                metadata=result.metadata,
            )
            await db.commit()

            logger.debug(f"Saved notification log for result {context.result_id}")

        except Exception as e:
            logger.error(f"Failed to save notification log: {e}", exc_info=True)
            # Don't re-raise - logging failure shouldn't break notification


class PipelineOrchestrator:
    """
    High-level orchestrator that manages multiple pipelines.

    Allows running multiple pipelines for a single result
    (e.g., send to both email and xiaohongshu).
    """

    def __init__(self, pipelines: List[NotificationPipeline]):
        """
        Initialize orchestrator with pipelines.

        Args:
            pipelines: List of pipelines to run
        """
        self.pipelines = pipelines

    async def execute_all(
        self,
        context: NotificationContext,
        db: AsyncSession,
    ) -> List[NotificationResult]:
        """
        Execute all registered pipelines.

        Args:
            context: Notification context
            db: Database session

        Returns:
            List of NotificationResult (one per pipeline)
        """
        results = []

        for pipeline in self.pipelines:
            try:
                # Create a copy of context for each pipeline
                # (so processors in one pipeline don't affect others)
                pipeline_context = self._clone_context(context)
                pipeline_context.pipeline_name = pipeline.name

                result = await pipeline.execute(pipeline_context, db)
                results.append(result)

            except Exception as e:
                logger.error(f"Pipeline '{pipeline.name}' crashed: {e}", exc_info=True)
                # Continue with other pipelines

        return results

    def _clone_context(self, context: NotificationContext) -> NotificationContext:
        """Create a shallow copy of context for pipeline isolation."""
        return NotificationContext(
            result_id=context.result_id,
            result_text=context.result_text,
            favorite_item=context.favorite_item,
            workshop=context.workshop,
            metadata=context.metadata.copy(),
            pipeline_name=context.pipeline_name,
        )
