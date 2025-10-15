"""
Image Renderer Processor

Renders text content as beautiful images using EAI RPC service.
"""

import base64
from typing import Dict, Optional, Tuple

from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.notifications.context import NotificationContext
from client_sdk.params import ServiceParams, TaskParams
from client_sdk.rpc_client_async import EAIRPCClient

logger = get_logger(__name__)


class ImageRendererProcessor:
    """
    Renders text content as images using EAI RPC service.

    This processor calls the external image rendering service
    to create visually appealing cards from text content.
    """

    def __init__(
        self,
        style: str = "minimal_card",
        size: Optional[Tuple[int, int]] = None,
        timeout_sec: int = 120,
        rpc_client: Optional[EAIRPCClient] = None,
    ):
        """
        Initialize image renderer.

        Args:
            style: Rendering style template (e.g., "minimal_card", "elegant_card")
            size: Image size as (width, height) tuple. Defaults to (1080, 1920)
            timeout_sec: RPC timeout in seconds
            rpc_client: Optional pre-configured RPC client (for testing/reuse)
        """
        self.style = style
        self.size = size or (1080, 1920)
        self.timeout_sec = timeout_sec
        self._rpc_client = rpc_client

    def _get_rpc_client(self) -> EAIRPCClient:
        """Get or create RPC client instance."""
        if self._rpc_client:
            return self._rpc_client

        # Create client from settings
        return EAIRPCClient(
            base_url=settings.EAI_BASE_URL,
            api_key=settings.EAI_API_KEY,
        )

    async def process(self, context: NotificationContext) -> NotificationContext:
        """
        Render text content as image using EAI service.

        Args:
            context: Notification context

        Returns:
            Modified context with rendered_image_data set
        """
        try:
            # Use formatted text if available, otherwise raw text
            content = context.get_display_text()
            title = context.get_item_title()

            # Prepare metadata for rendering
            metadata = self._prepare_metadata(context)

            logger.info(
                f"Rendering image for result {context.result_id}, "
                f"style={self.style}, size={self.size}"
            )

            # Get RPC client
            client = self._get_rpc_client()
            client_needs_cleanup = self._rpc_client is None

            try:
                # Start client if not already started
                if not client._http_client:
                    await client.start()

                # Call render_image RPC
                result = await client.render_image(
                    content=content,
                    title=title,
                    style=self.style,
                    size=self.size,
                    metadata=metadata,
                    rpc_timeout_sec=self.timeout_sec,
                    task_params=TaskParams(),
                    service_params=ServiceParams(),
                )

                # Extract image data from result
                image_data = result.get("image_data")
                if not image_data:
                    raise ValueError("No image_data in render result")

                # Decode base64 if needed
                if isinstance(image_data, str):
                    image_bytes = base64.b64decode(image_data)
                else:
                    image_bytes = image_data

                # Store in context
                context.rendered_image_data = image_bytes
                context.rendered_image_url = result.get("image_url")

                # Store render info in metadata
                context.metadata["image_format"] = result.get("format", "png")
                context.metadata["image_width"] = result.get("width", self.size[0])
                context.metadata["image_height"] = result.get("height", self.size[1])

                context.mark_processed_by("image_renderer")

                logger.info(
                    f"Image rendered successfully: {len(image_bytes)} bytes, "
                    f"format={result.get('format')}"
                )

            finally:
                # Cleanup client if we created it
                if client_needs_cleanup:
                    await client.stop()

        except Exception as e:
            error_msg = f"Image rendering failed: {e}"
            logger.error(error_msg, exc_info=True)
            context.add_error(error_msg)
            # Don't fail the entire pipeline - continue without image

        return context

    def _prepare_metadata(self, context: NotificationContext) -> Dict:
        """Prepare metadata for image rendering."""
        metadata = {}

        # Add item information
        item = context.favorite_item
        if item:
            metadata["platform"] = context.get_item_platform()
            if item.author:
                metadata["author"] = item.author.username

            # Add statistics if available (for Bilibili videos)
            if hasattr(item, "bilibili_video_details") and item.bilibili_video_details:
                details = item.bilibili_video_details
                metadata["stats"] = {
                    "view_count": details.view_count,
                    "like_count": details.like_count,
                    "coin_count": details.coin_count,
                }

            # Add tags
            if item.tags:
                metadata["tags"] = [tag.name for tag in item.tags[:5]]  # Limit to 5 tags

        # Add workshop information
        metadata["workshop_name"] = context.workshop.name

        return metadata
