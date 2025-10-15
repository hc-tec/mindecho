import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable

from app.core.config import settings
from app.core.websocket_manager import manager as websocket_manager
from client_sdk.rpc_client_async import EAIRPCClient


logger = logging.getLogger(__name__)


class StreamManager:
    """Manage long-running plugin streams and fan out events.

    - Starts a single EAIRPCClient instance per process
    - Tracks running asyncio tasks keyed by stream_id
    - Broadcasts events via websocket_manager (group or direct)
    """

    def __init__(self) -> None:
        self.client = EAIRPCClient(
            base_url=settings.EAI_BASE_URL,
            api_key=settings.EAI_API_KEY,
            webhook_port=0,
        )
        self._tasks: Dict[str, asyncio.Task] = {}
        self._remote_task_ids: Dict[str, str] = {}
        self._running: bool = False
        self._on_event: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None

    async def start(self) -> None:
        if self._running:
            return
        await self.client.start()
        self._running = True

    async def stop(self) -> None:
        for task in list(self._tasks.values()):
            task.cancel()
        self._tasks.clear()
        if self._running:
            await self.client.stop()
            self._running = False

    def list_streams(self) -> List[str]:
        return list(self._tasks.keys())

    def register_event_handler(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Register a coroutine to handle each incoming stream event.

        Handler signature: async def handler(event: Dict[str, Any]) -> None
        """
        self._on_event = handler

    def start_stream(
        self,
        *,
        stream_id: str,
        plugin_id: str,
        group: Optional[str] = None,
        run_mode: str = "recurring",
        interval: float = 300,
        buffer_size: int = 100,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        if stream_id in self._tasks:
            return stream_id
        task = asyncio.create_task(
            self._run_stream_task(
                stream_id=stream_id,
                plugin_id=plugin_id,
                group=group,
                run_mode=run_mode,
                interval=interval,
                buffer_size=buffer_size,
                params=params or {},
            )
        )
        self._tasks[stream_id] = task
        return stream_id

    def stop_stream(self, stream_id: str) -> bool:
        """Stop local stream task and delete remote plugin task.

        We assume the remote task ID equals the provided ``stream_id`` unless
        another convention is introduced later. If you store explicit task IDs
        elsewhere, replace the fallback accordingly.
        """
        task = self._tasks.pop(stream_id, None)
        if task:
            task.cancel()

            # Find real remote task id if recorded
            remote_id = self._remote_task_ids.pop(stream_id, None) or stream_id

            # Fire-and-forget deletion of the remote task to avoid blocking.
            async def _delete() -> None:  # pragma: no cover – best-effort cleanup
                try:
                    await self.client.delete_task(remote_id)
                except Exception:
                    logger.exception("Failed to delete remote task %s for stream %s", remote_id, stream_id)

            asyncio.create_task(_delete())
            return True
        return False

    async def _run_stream_task(
        self,
        *,
        stream_id: str,
        plugin_id: str,
        group: Optional[str],
        run_mode: str,
        interval: float,
        buffer_size: int,
        params: Dict[str, Any],
    ) -> None:
        try:
            async with self.client.run_plugin_stream(
                plugin_id=plugin_id,
                run_mode=run_mode,  # type: ignore[arg-type]
                interval=interval,
                buffer_size=buffer_size,
                **params,
            ) as stream:
                # Record remote task id if provided by client
                remote_id: Optional[str] = getattr(stream, "remote_task_id", None)
                if remote_id:
                    self._remote_task_ids[stream_id] = remote_id
                while True:
                    try:
                        event = await stream.next(timeout=60)

                        # CRITICAL: Inject stream params into event for downstream handlers
                        # RPC plugins don't return params in events, but handlers need them
                        # (e.g., collection_id to associate items with collections)
                        event["params"] = params
                        event["stream_id"] = stream_id

                        # if group:
                        #     await websocket_manager.broadcast_json(group, event)
                        # else:
                        #     await websocket_manager.send_json(stream_id, event)
                        if self._on_event:
                            # Best-effort: do not block broadcast path
                            asyncio.create_task(self._on_event(event))
                    except TimeoutError:
                        logger.debug("⌛ 60s内未收到事件，继续等待...")
                        continue
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Stream %s for plugin %s crashed", stream_id, plugin_id)
        finally:
            self._tasks.pop(stream_id, None)


# Global singleton used across the app
stream_manager = StreamManager()


