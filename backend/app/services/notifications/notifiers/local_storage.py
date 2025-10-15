"""
Local Storage Notifier

Saves notifications to local filesystem for manual review/sharing.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.logging_config import get_logger
from app.services.notifications.context import (
    NotificationContext,
    NotificationResult,
    NotificationStatus,
)

logger = get_logger(__name__)


class LocalStorageNotifier:
    """
    Saves notification content to local filesystem.

    This notifier serves as:
    1. MVP fallback when no external channels configured
    2. Audit trail for all notifications
    3. Manual sharing option for users
    """

    def __init__(
        self,
        output_dir: str = "./notifications",
        organize_by_date: bool = True,
        save_images: bool = True,
        save_metadata: bool = True,
    ):
        """
        Initialize local storage notifier.

        Args:
            output_dir: Base directory for saving notifications
            organize_by_date: Organize files by date (YYYY-MM-DD subdirectories)
            save_images: Save rendered images if available
            save_metadata: Save metadata JSON alongside content
        """
        self.output_dir = Path(output_dir)
        self.organize_by_date = organize_by_date
        self.save_images = save_images
        self.save_metadata = save_metadata

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def send(self, context: NotificationContext) -> NotificationResult:
        """
        Save notification to local filesystem.

        Args:
            context: Notification context

        Returns:
            NotificationResult with success/failure status
        """
        try:
            # Determine target directory
            target_dir = self._get_target_directory()
            target_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename base
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            item_id = context.favorite_item.id
            filename_base = f"{timestamp}_result_{context.result_id}_item_{item_id}"

            # Save text content
            text_path = target_dir / f"{filename_base}.txt"
            text_content = context.get_display_text()
            text_path.write_text(text_content, encoding="utf-8")

            logger.info(f"Saved text notification to {text_path}")

            # Save image if available
            image_path = None
            if self.save_images and context.rendered_image_data:
                image_format = context.metadata.get("image_format", "png")
                image_path = target_dir / f"{filename_base}.{image_format}"
                image_path.write_bytes(context.rendered_image_data)
                logger.info(f"Saved image notification to {image_path}")

            # Save metadata if requested
            metadata_path = None
            if self.save_metadata:
                metadata_path = target_dir / f"{filename_base}_meta.json"
                metadata = self._build_metadata(context, text_path, image_path)
                metadata_path.write_text(
                    json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                logger.debug(f"Saved metadata to {metadata_path}")

            # Return success result
            return NotificationResult(
                status=NotificationStatus.SUCCESS,
                notifier_type="local_storage",
                sent_at=datetime.utcnow(),
                external_id=str(text_path),  # Use file path as external ID
                metadata={
                    "text_path": str(text_path),
                    "image_path": str(image_path) if image_path else None,
                    "metadata_path": str(metadata_path) if metadata_path else None,
                },
            )

        except Exception as e:
            error_msg = f"Failed to save notification to local storage: {e}"
            logger.error(error_msg, exc_info=True)

            return NotificationResult(
                status=NotificationStatus.FAILED,
                notifier_type="local_storage",
                sent_at=datetime.utcnow(),
                error_message=error_msg,
            )

    def _get_target_directory(self) -> Path:
        """Get target directory for saving files."""
        if self.organize_by_date:
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            return self.output_dir / date_str
        return self.output_dir

    def _build_metadata(
        self,
        context: NotificationContext,
        text_path: Path,
        image_path: Optional[Path],
    ) -> dict:
        """Build metadata dict for JSON export."""
        item = context.favorite_item

        metadata = {
            "notification": {
                "result_id": context.result_id,
                "pipeline_name": context.pipeline_name,
                "created_at": datetime.utcnow().isoformat(),
                "processed_by": context.processed_by,
                "errors": context.errors,
            },
            "files": {
                "text": str(text_path),
                "image": str(image_path) if image_path else None,
            },
            "source_item": {
                "id": item.id,
                "title": item.title,
                "platform": context.get_item_platform(),
                "platform_item_id": item.platform_item_id,
                "author": item.author.username if item.author else None,
                "favorited_at": item.favorited_at.isoformat() if item.favorited_at else None,
            },
            "workshop": {
                "id": context.workshop.workshop_id,
                "name": context.workshop.name,
            },
            "context_metadata": context.metadata,
        }

        return metadata
