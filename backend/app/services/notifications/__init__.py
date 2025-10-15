"""
Notification System Module

Provides a pluggable, pipeline-based notification system for MindEcho.
Follows clean architecture principles with Protocol-based dependency injection.
"""

from app.services.notifications.context import (
    NotificationContext,
    NotificationResult,
    NotificationStatus,
)
from app.services.notifications.protocols import ResultNotifier, ResultProcessor
from app.services.notifications.registry import (
    get_notifier,
    get_processor,
    notifier_registry,
    processor_registry,
    register_notifier,
    register_processor,
)

__all__ = [
    # Context & Results
    "NotificationContext",
    "NotificationResult",
    "NotificationStatus",
    # Protocols
    "ResultProcessor",
    "ResultNotifier",
    # Registry
    "processor_registry",
    "notifier_registry",
    "register_processor",
    "register_notifier",
    "get_processor",
    "get_notifier",
]
