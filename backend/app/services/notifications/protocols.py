"""
Notification System Protocols

This module defines the core protocols (interfaces) for the notification system.
Following the same clean architecture pattern as stream_event_handler.py.
"""

from typing import Protocol

from app.services.notifications.context import NotificationContext, NotificationResult


class ResultProcessor(Protocol):
    """
    Protocol for processing workshop results before notification.

    Processors transform the content (formatting, rendering, adapting)
    without sending notifications. They modify the NotificationContext
    and pass it along the pipeline.

    Examples: TextFormatter, ImageRenderer, ContentAdapter, PrivacyFilter
    """

    async def process(self, context: NotificationContext) -> NotificationContext:
        """
        Process the notification context and return modified context.

        Args:
            context: Current notification context

        Returns:
            Modified notification context

        Raises:
            Exception: Processing errors should be caught and added to context.errors
        """
        ...


class ResultNotifier(Protocol):
    """
    Protocol for sending notifications through various channels.

    Notifiers are responsible for the actual delivery of notifications
    to external systems or local storage. They consume the processed
    context and return delivery status.

    Examples: EmailNotifier, XiaohongshuNotifier, TelegramNotifier
    """

    async def send(self, context: NotificationContext) -> NotificationResult:
        """
        Send notification using the processed context.

        Args:
            context: Fully processed notification context

        Returns:
            NotificationResult with success/failure status

        Raises:
            Exception: Send errors should be caught and returned in NotificationResult
        """
        ...
