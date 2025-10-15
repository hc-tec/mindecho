"""
Plugin Registry for Notification System

Manages registration and retrieval of processors and notifiers.
"""

from typing import Dict, Generic, Optional, TypeVar

from app.core.logging_config import get_logger
from app.services.notifications.protocols import ResultNotifier, ResultProcessor

logger = get_logger(__name__)

T = TypeVar("T")


class PluginRegistry(Generic[T]):
    """
    Generic plugin registry for processors and notifiers.

    Supports registration, retrieval, and listing of plugins.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._plugins: Dict[str, T] = {}

    def register(self, name: str, plugin: T) -> None:
        """
        Register a plugin with a given name.

        Args:
            name: Unique identifier for the plugin
            plugin: The plugin instance

        Raises:
            ValueError: If plugin name already exists
        """
        if name in self._plugins:
            logger.warning(f"Plugin '{name}' already registered, overwriting")

        self._plugins[name] = plugin
        logger.info(f"Registered plugin: {name}")

    def get(self, name: str) -> Optional[T]:
        """
        Retrieve a plugin by name.

        Args:
            name: Plugin identifier

        Returns:
            Plugin instance or None if not found
        """
        plugin = self._plugins.get(name)
        if not plugin:
            logger.warning(f"Plugin '{name}' not found in registry")
        return plugin

    def has(self, name: str) -> bool:
        """Check if plugin exists in registry."""
        return name in self._plugins

    def list_names(self) -> list[str]:
        """Get list of all registered plugin names."""
        return list(self._plugins.keys())

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        logger.info("Plugin registry cleared")


# Global registries
processor_registry: PluginRegistry[ResultProcessor] = PluginRegistry()
notifier_registry: PluginRegistry[ResultNotifier] = PluginRegistry()


def register_processor(name: str, processor: ResultProcessor) -> None:
    """
    Convenience function to register a processor.

    Args:
        name: Processor identifier
        processor: Processor instance
    """
    processor_registry.register(name, processor)


def register_notifier(name: str, notifier: ResultNotifier) -> None:
    """
    Convenience function to register a notifier.

    Args:
        name: Notifier identifier
        notifier: Notifier instance
    """
    notifier_registry.register(name, notifier)


def get_processor(name: str) -> Optional[ResultProcessor]:
    """Get a registered processor by name."""
    return processor_registry.get(name)


def get_notifier(name: str) -> Optional[ResultNotifier]:
    """Get a registered notifier by name."""
    return notifier_registry.get(name)
