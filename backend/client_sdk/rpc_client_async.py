#!/usr/bin/env python3
"""
Fully asynchronous RPC client using httpx and aiohttp.
- httpx.AsyncClient for outgoing RPC calls.
- aiohttp.web for the embedded webhook server.
- Runs entirely within a single event loop, compatible with FastAPI.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
import socket
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Literal

import httpx
from aiohttp import web

from client_sdk.params import TaskParams, ServiceParams

logger = logging.getLogger("eai_rpc_client_async")


class _PendingCall:
    """A pending RPC call waiting for a webhook callback."""
    def __init__(self, event_id: str, future: asyncio.Future, timeout: float = 300.0):
        self.event_id = event_id
        self.future = future
        self.timeout = timeout
        self.created_at = time.time()
    
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.timeout


class _LRUIdCache:
    """LRU cache for event deduplication."""
    def __init__(self, capacity: int = 2048) -> None:
        self.capacity = capacity
        self._store: OrderedDict[str, float] = OrderedDict()

    def add_if_new(self, key: str) -> bool:
        if key in self._store:
            self._store.move_to_end(key)
            return False
        self._store[key] = time.time()
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)
        return True


class EAIRPCClient:
    """Fully asynchronous Everything-as-an-Interface RPC Client."""
    
    def __init__(
        self, 
        base_url: str, 
        api_key: str,
        webhook_host: str = "127.0.0.1",
        webhook_port: int = 0, # Auto-assign port by default
        webhook_secret: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.webhook_host = webhook_host
        self.webhook_port = webhook_port
        self.webhook_secret = webhook_secret or str(uuid.uuid4())
        
        self._http_client: Optional[httpx.AsyncClient] = None
        self._webhook_runner: Optional[web.AppRunner] = None
        self._webhook_site: Optional[web.TCPSite] = None
        
        self._pending_calls: Dict[str, _PendingCall] = {}
        self._events_seen = _LRUIdCache()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._topic_listeners: Dict[str, List[asyncio.Queue]] = {}

    class _Stream:
        def __init__(self, queue: asyncio.Queue, topic_id: str, registry: Dict[str, List[asyncio.Queue]]):
            self._queue = queue
            self._closed = False
            self._topic_id = topic_id
            self._registry = registry

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._closed:
                raise StopAsyncIteration
            item = await self._queue.get()
            return item

        async def next(self, timeout: Optional[float] = None):
            try:
                if timeout is None:
                    return await self._queue.get()
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError("listen timeout")

        async def close(self):
            if not self._closed:
                self._closed = True
                try:
                    listeners = self._registry.get(self._topic_id, [])
                    if self._queue in listeners:
                        listeners.remove(self._queue)
                    if not listeners and self._topic_id in self._registry:
                        self._registry.pop(self._topic_id, None)
                except Exception:
                    pass

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """aiohttp handler for incoming webhooks."""
        x_eai_event_id = request.headers.get("X-EAI-EVENT-ID")
        x_eai_signature = request.headers.get("X-EAI-SIGNATURE")
        x_eai_topic_id = request.headers.get("X-EAI-TOPIC-ID")
        x_eai_plugin_id = request.headers.get("X-EAI-PLUGIN-ID")
        
        raw_body = await request.read()
        
        if self.webhook_secret and x_eai_signature:
            if not self._verify_signature(self.webhook_secret, raw_body, x_eai_signature):
                return web.Response(status=401, text="Invalid signature")

        if x_eai_event_id and not self._events_seen.add_if_new(x_eai_event_id):
            return web.json_response({"ok": True, "duplicate": True})

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return web.Response(status=400, text="Invalid JSON payload")

        # Fan out to any listeners registered for this topic (streaming mode)
        if x_eai_topic_id and x_eai_topic_id in self._topic_listeners:
            listeners = list(self._topic_listeners.get(x_eai_topic_id, []))
            event = {
                "event_id": x_eai_event_id,
                "topic_id": x_eai_topic_id,
                "plugin_id": x_eai_plugin_id,
                "payload": payload,
            }
            for q in listeners:
                try:
                    q.put_nowait(event)
                except Exception:
                    # Ignore a single listener queue failure to avoid blocking others
                    pass

        if x_eai_topic_id in self._pending_calls:
            pending = self._pending_calls.pop(x_eai_topic_id)
            if not pending.future.done():
                result = payload.get("result", {})
                if payload.get("success", True):
                    pending.future.set_result(result)
                else:
                    error_msg = payload.get("error", "Unknown error")
                    pending.future.set_exception(Exception(error_msg))
        
        return web.json_response({"ok": True})
    
    def _verify_signature(self, secret: str, raw_body: bytes, signature_header: str) -> bool:
        try:
            scheme, hexdigest = signature_header.split("=", 1)
            if scheme.lower() != "sha256": return False
            expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, hexdigest)
        except Exception:
            return False
    
    async def _cleanup_expired_calls(self):
        while True:
            await asyncio.sleep(30)
            expired_keys = [
                event_id for event_id, pending in self._pending_calls.items() if pending.is_expired()
            ]
            for key in expired_keys:
                pending = self._pending_calls.pop(key, None)
                if pending and not pending.future.done():
                    pending.future.set_exception(TimeoutError("RPC call timeout"))
    
    async def start(self):
        self._http_client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            http2=False,
            timeout=60.0,
        )

        # Auto-assign port if set to 0
        if self.webhook_port == 0:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 0))
                self.webhook_port = s.getsockname()[1]

        app = web.Application()
        app.add_routes([web.post('/webhook', self._handle_webhook)])
        self._webhook_runner = web.AppRunner(app)
        await self._webhook_runner.setup()
        self._webhook_site = web.TCPSite(self._webhook_runner, self.webhook_host, self.webhook_port)
        await self._webhook_site.start()
        
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_calls())
        logger.info(f"EAIRPCClient started. Webhook receiver listening on http://{self.webhook_host}:{self.webhook_port}/webhook")

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._webhook_runner:
            await self._webhook_runner.cleanup()
        if self._http_client:
            await self._http_client.aclose()
        logger.info("EAIRPCClient stopped.")

    @asynccontextmanager
    async def _rpc_call(self, plugin_id: str, params: Dict[str, Any], timeout_sec: float):
        if not self._http_client:
            raise RuntimeError("Client not started. Please call 'await client.start()' first.")
            
        event_id = str(uuid.uuid4())
        topic_id = f"rpc-{event_id}"
        webhook_url = f"http://{self.webhook_host}:{self.webhook_port}/webhook"

        try:
            # Setup topic and subscription
            await self._http_client.post("/api/v1/topics", json={"topic_id": topic_id, "name": topic_id, "description": f"RPC for {plugin_id}"})
            await self._http_client.post(f"/api/v1/topics/{topic_id}/subscriptions", json={"url": webhook_url, "secret": self.webhook_secret})
            
            # Prepare for result
            future = asyncio.Future()
            self._pending_calls[topic_id] = _PendingCall(topic_id, future, timeout_sec)
            
            # Execute plugin
            await self._http_client.post("/api/v1/tasks", json={"plugin_id": plugin_id, "run_mode": "once", "params": params, "topic_id": topic_id})

            result = await asyncio.wait_for(future, timeout=timeout_sec)
            yield result
        
        except asyncio.TimeoutError:
            raise TimeoutError(f"RPC call for '{plugin_id}' timed out after {timeout_sec} seconds.")
        finally:
            self._pending_calls.pop(topic_id, None)

    def _merge_params(self, task_params, service_params, extra_params):
        return {k: v for k, v in {**task_params.__dict__, **service_params.__dict__, **extra_params}.items() if v is not None}

    # --- Public RPC Methods ---
    async def get_collection_list_from_bilibili(self, user_id: Optional[str]=None, rpc_timeout_sec=60, task_params: TaskParams=TaskParams(), service_params: ServiceParams=ServiceParams()):
        params = self._merge_params(task_params, service_params, {"user_id": user_id})
        async with self._rpc_call("bilibili_collection_list", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    async def get_collection_list_videos_from_bilibili(self, collection_id: str, user_id: Optional[str]=None, rpc_timeout_sec=120, task_params: TaskParams=TaskParams(), service_params: ServiceParams=ServiceParams()):
        params = self._merge_params(task_params, service_params, {"collection_id": collection_id, "user_id": user_id})
        async with self._rpc_call("bilibili_collection_videos", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    async def get_video_details_from_bilibili(self, bvid: str, rpc_timeout_sec=60, task_params: TaskParams=TaskParams(), service_params: ServiceParams=ServiceParams()):
        params = self._merge_params(task_params, service_params, {"bvid": bvid})
        async with self._rpc_call("bilibili_video_details", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    async def chat_with_yuanbao(self, ask_question: str, conversation_id: str, rpc_timeout_sec=60, task_params: TaskParams=TaskParams(), service_params: ServiceParams=ServiceParams()):
        ask_question = ask_question.replace('\n', '').replace('\r', '')
        params = self._merge_params(task_params, service_params, {"ask_question": ask_question})
        async with self._rpc_call("yuanbao_chat", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    # --- Utility / management RPCs ---
    async def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a running or finished task on the server.

        Mirrors backend endpoint: DELETE /api/v1/tasks/{task_id}
        Returns the backend JSON response (usually {"ok": true} or similar).
        """
        if not self._http_client:
            raise RuntimeError("Client not started. Please call 'await client.start()' first.")

        resp = await self._http_client.delete(f"/api/v1/tasks/{task_id}")
        resp.raise_for_status()
        # Some servers may return empty body
        try:
            return resp.json()
        except ValueError:
            return {"ok": True}

    # --- Streaming RPC ---
    @asynccontextmanager
    async def run_plugin_stream(
        self,
        plugin_id: str,
        run_mode: Literal["once", "recurring"] = "recurring",
        interval: float = 300,
        buffer_size: int = 100,
        task_params: TaskParams = TaskParams(),
        service_params: ServiceParams = ServiceParams(),
        **kwargs: Any,
    ):
        """Start a plugin and stream multiple events from its topic.

        Yields an async-iterable stream object. Each item is a dict:
        {"event_id", "topic_id", "plugin_id", "payload"}
        """
        if not self._http_client:
            raise RuntimeError("Client not started. Please call 'await client.start()' first.")

        params: Dict[str, Any] = self._merge_params(task_params, service_params, kwargs)

        # Prepare topic and subscription
        topic_id = f"stream-{uuid.uuid4()}"
        webhook_url = f"http://{self.webhook_host}:{self.webhook_port}/webhook"

        # Create topic
        resp = await self._http_client.post(
            "/api/v1/topics",
            json={"topic_id": topic_id, "name": topic_id, "description": f"Stream for {plugin_id}"},
        )
        resp.raise_for_status()

        # Create subscription
        resp = await self._http_client.post(
            f"/api/v1/topics/{topic_id}/subscriptions",
            json={"url": webhook_url, "secret": self.webhook_secret},
        )
        resp.raise_for_status()

        # Register a listener queue
        queue: asyncio.Queue = asyncio.Queue(maxsize=buffer_size)
        self._topic_listeners.setdefault(topic_id, []).append(queue)
        stream = self._Stream(queue, topic_id, self._topic_listeners)

        try:
            # Start the plugin task
            resp = await self._http_client.post(
                "/api/v1/tasks",
                json={
                    "plugin_id": plugin_id,
                    "run_mode": run_mode,
                    "params": params,
                    "topic_id": topic_id,
                    "interval": interval,
                },
            )
            resp.raise_for_status()
            try:
                task_payload = resp.json()
                remote_task_id = task_payload.get("task_id") or task_payload.get("id")
            except Exception:
                remote_task_id = None

            # Expose remote task id on stream for callers who want to manage lifecycle
            setattr(stream, "remote_task_id", remote_task_id)

            yield stream
        finally:
            await stream.close()

    @asynccontextmanager
    async def listen_topic(self, topic_id: str, buffer_size: int = 100):
        """Listen to an existing topic without creating a new task.

        Assumes the server already has the topic and a subscription for this client's webhook.
        Yields an async-iterable stream object producing dict events:
        {"event_id", "topic_id", "plugin_id", "payload"}
        """
        if not self._http_client:
            raise RuntimeError("Client not started. Please call 'await client.start()' first.")

        queue: asyncio.Queue = asyncio.Queue(maxsize=buffer_size)
        self._topic_listeners.setdefault(topic_id, []).append(queue)
        stream = self._Stream(queue, topic_id, self._topic_listeners)
        try:
            yield stream
        finally:
            await stream.close()
