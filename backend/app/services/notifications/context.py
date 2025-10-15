"""
Notification Context and Result Data Structures

Defines the data structures passed through the notification pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.db.models import FavoriteItem, Workshop


class NotificationStatus(str, Enum):
    """Status of notification delivery."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class NotificationResult:
    """
    Result of a notification send operation.

    This is returned by notifiers to indicate success/failure.
    """

    status: NotificationStatus
    notifier_type: str
    sent_at: datetime
    error_message: Optional[str] = None
    external_id: Optional[str] = None  # External platform ID (e.g., Xiaohongshu note ID)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        """Check if notification was successful."""
        return self.status == NotificationStatus.SUCCESS


@dataclass
class NotificationContext:
    """
    Context object passed through the notification pipeline.

    This carries all information needed for processing and sending notifications.
    Processors modify this context, and notifiers consume it.
    """

    # Source data (immutable references)
    result_id: int  # WorkshopResult ID
    result_text: str  # Raw result content from workshop
    favorite_item: FavoriteItem  # The item being notified about
    workshop: Workshop  # The workshop that generated the result

    # Processed content (modified by processors)
    formatted_text: Optional[str] = None  # Text after formatting
    rendered_image_data: Optional[bytes] = None  # Image binary data
    rendered_image_url: Optional[str] = None  # Image URL (if uploaded)
    html_content: Optional[str] = None  # HTML formatted content

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    pipeline_name: str = "default"

    # Processing tracking
    processed_by: List[str] = field(default_factory=list)  # List of processor names
    errors: List[str] = field(default_factory=list)  # Non-fatal errors during processing

    def mark_processed_by(self, processor_name: str) -> None:
        """Mark context as processed by a specific processor."""
        self.processed_by.append(processor_name)

    def add_error(self, error: str) -> None:
        """Add a non-fatal error to the context."""
        self.errors.append(error)

    def has_errors(self) -> bool:
        """Check if any errors occurred during processing."""
        return bool(self.errors)

    def get_display_text(self) -> str:
        """Get the best available text for display (formatted or raw)."""
        return self.formatted_text or self.result_text

    def get_item_title(self) -> str:
        """Get the favorite item's title."""
        return self.favorite_item.title or "Untitled"

    def get_item_platform(self) -> str:
        """Get the favorite item's platform."""
        return self.favorite_item.platform.value if self.favorite_item.platform else "unknown"
