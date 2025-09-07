#!/usr/bin/env python3
"""
RPC风格的客户端SDK

提供类似RPC的接口，自动处理webhook注册、任务执行和结果等待。
使用示例:
    client_sdk = EAIRPCClient("http://localhost:8000", api_key="your-key")
    result = await client_sdk.chat_with_yuanbao("你好，请介绍一下自己")
    notes = await client_sdk.get_favorite_notes_brief_from_xhs(["美食", "旅行"], max_items=50)
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
from typing import Any, Dict, List, Optional, Callable, Awaitable, Literal

import requests
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from client_sdk.params import TaskParams, ServiceParams, SyncParams

logger = logging.getLogger("eai_rpc_client")


async def async_request(req_session: requests.Session, method: str, url: str, **kwargs):
    return await asyncio.to_thread(lambda: req_session.request(method, url, **kwargs))


class _PendingCall:
    """等待中的RPC调用"""
    def __init__(self, event_id: str, future: asyncio.Future, timeout: float = 300.0):
        self.event_id = event_id
        self.future = future
        self.timeout = timeout
        self.created_at = time.time()
    
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.timeout


class _LRUIdCache:
    """LRU缓存，用于去重"""
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
    """Everything-as-an-Interface RPC客户端"""
    
    def __init__(
        self, 
        base_url: str, 
        api_key: str,
        webhook_host: str = "0.0.0.0",
        webhook_port: int = 9001,
        webhook_secret: Optional[str] = None,
    ):
        self._server_task = None
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.webhook_host = webhook_host
        self.webhook_port = webhook_port
        self.webhook_secret = webhook_secret or str(uuid.uuid4())
        
        # HTTP客户端
        # requests 会话
        self.http_client = requests.Session()
        self.http_client.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })
        
        # Webhook服务器
        self.webhook_app = FastAPI(title="EAI RPC Webhook Receiver")
        self._setup_webhook_routes()
        
        # 等待中的调用
        self._pending_calls: Dict[str, _PendingCall] = {}
        self._events_seen = _LRUIdCache()
        # 新增：主题监听者注册表（每个topic维护一个队列列表，实现多结果监听）
        self._topic_listeners: Dict[str, List[asyncio.Queue]] = {}
        
        # 服务器状态
        self._webhook_server: Optional[uvicorn.Server] = None
        self._cleanup_task = None
    
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
    
    def _setup_webhook_routes(self):
        """设置webhook路由"""
        @self.webhook_app.get("/health")
        async def health_check():
            """健康检查端点"""
            return {"status": "ok", "service": "eai-rpc-webhook"}
        
        @self.webhook_app.post("/webhook")
        async def receive_webhook(
            request: Request,
            x_eai_event_id: Optional[str] = Header(default=None),
            x_eai_signature: Optional[str] = Header(default=None),
            x_eai_topic_id: Optional[str] = Header(default=None),
            x_eai_plugin_id: Optional[str] = Header(default=None),
        ) -> Dict[str, Any]:
            raw = await request.body()
            
            # 验证签名
            if self.webhook_secret and x_eai_signature:
                if not self._verify_signature(self.webhook_secret, raw, x_eai_signature):
                    raise HTTPException(status_code=401, detail="Invalid signature")
            
            # 去重
            event_id = x_eai_event_id or ""
            if event_id:
                is_new = self._events_seen.add_if_new(event_id)
                if not is_new:
                    return {"ok": True, "duplicate": True}
            
            # 解析payload
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                payload = {"raw": raw.decode("utf-8", errors="replace")}
            
            # 以topic_id为键进行分发（支持长期监听多个结果）
            match_key = x_eai_topic_id
            if match_key and match_key in self._topic_listeners:
                listeners = list(self._topic_listeners.get(match_key, []))
                event = {
                    "event_id": event_id,
                    "topic_id": x_eai_topic_id,
                    "plugin_id": x_eai_plugin_id,
                    "payload": payload,
                }
                for q in listeners:
                    try:
                        q.put_nowait(event)
                    except Exception:
                        # 忽略单个监听队列的异常，避免影响整体分发
                        pass
            
            # 处理等待中的调用（通过topic_id匹配）
            if match_key in self._pending_calls:
                pending = self._pending_calls.pop(match_key)
                if not pending.future.done():
                    result = payload.get("result", {})
                    if payload.get("success", True):
                        pending.future.set_result(result)
                    else:
                        error_msg = payload.get("error", "Unknown error")
                        pending.future.set_exception(Exception(error_msg))
            
            logger.info(
                "Received webhook: event_id=%s, topic_id=%s, plugin_id=%s",
                event_id, x_eai_topic_id, x_eai_plugin_id
            )
            
            return {"ok": True}
    
    def _verify_signature(self, secret: str, raw_body: bytes, signature_header: str) -> bool:
        """验证HMAC签名"""
        try:
            scheme, hexdigest = signature_header.split("=", 1)
            if scheme.lower() != "sha256":
                return False
            expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected, hexdigest)
        except Exception:
            return False
    
    async def _cleanup_expired_calls(self):
        """清理过期的调用"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                expired_keys = []
                for event_id, pending in self._pending_calls.items():
                    if pending.is_expired():
                        expired_keys.append(event_id)
                        if not pending.future.done():
                            pending.future.set_exception(TimeoutError("RPC call timeout"))
                
                for key in expired_keys:
                    self._pending_calls.pop(key, None)
                    
            except Exception as e:
                logger.error("Error in cleanup task: %s", e)
    
    async def start(self):
        """启动webhook服务器"""

        # 如果端口为0，自动分配可用端口
        if self.webhook_port == 0:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            self.webhook_port = sock.getsockname()[1]
            sock.close()
        
        config = uvicorn.Config(
            self.webhook_app,
            host=self.webhook_host,
            port=self.webhook_port,
            log_level="warning"  # 减少日志输出
        )
        self._webhook_server = uvicorn.Server(config)
        # 启动清理任务
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_calls())
        
        # 在后台启动服务器
        self._server_task = asyncio.create_task(self._webhook_server.serve())

    async def stop(self):
        """停止服务"""
        if self._cleanup_task:
            try:
                await self._cleanup_task.cancel()
            except asyncio.CancelledError:
                pass
            except TypeError:
                pass
        
        if hasattr(self, '_server_task') and self._server_task:
            try:
                await self._server_task.cancel()
            except asyncio.CancelledError:
                pass
            except TypeError:
                pass
        
        if self._webhook_server:
            self._webhook_server.should_exit = True
            try:
                await self._webhook_server.shutdown()
            except Exception as e:
                print("[NORMAL ERROR] clsoe webhook server: %s", e)
        
        await asyncio.to_thread(self.http_client.close)
    
    @asynccontextmanager
    async def _rpc_call(self,
                        plugin_id: str,
                        params: Dict[str, Any],
                        timeout_sec: float = 30.0):
        """执行RPC调用的上下文管理器"""
        # 生成唯一的事件ID
        event_id = str(uuid.uuid4())

        await self._test_health()
        
        # 创建topic
        topic_id = f"rpc-{event_id}"
        await self._create_topic(topic_id, f"RPC call for {plugin_id}")
        
        # 创建subscription
        webhook_host = self.webhook_host
        webhook_url = f"http://{webhook_host}:{self.webhook_port}/webhook"
        await self._create_subscription(topic_id, webhook_url)
        
        # 创建Future等待结果
        future = asyncio.Future()
        pending = _PendingCall(topic_id, future, timeout_sec)
        # 将pending挂载在topic_id下，方便通过topic_id回填结果
        self._pending_calls[topic_id] = pending
        
        try:
            # 执行插件
            await self._run_plugin(plugin_id, params, topic_id, run_mode="once")
            
            # 等待结果
            result = await asyncio.wait_for(future, timeout=timeout_sec)
            yield result
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"RPC call timeout after {timeout_sec} seconds")
        finally:
            # 清理
            self._pending_calls.pop(topic_id, None)

    async def _test_health(self):
        """测试是否正常连接"""
        response = await async_request(self.http_client, "GET", f"{self.base_url}/api/v1/health", timeout=30)
        try:
            ret = response.json()
            if ret.get("status") == "ok":
                pass
            else:
                raise RuntimeError()
        except Exception:
            print("❌ 服务似乎未正常启动")
        response.raise_for_status()
    
    async def _create_topic(self, topic_id: str, description: str):
        """创建topic"""
        response = await async_request(
            self.http_client,
            "post",
            f"{self.base_url}/api/v1/topics",
            json={
                "topic_id": topic_id,
                "name": topic_id,
                "description": description
            },
            timeout=30)
        response.raise_for_status()
    
    async def _create_subscription(self, topic_id: str, webhook_url: str):
        """创建subscription"""
        response = await async_request(
            self.http_client,
            "post",
            f"{self.base_url}/api/v1/topics/{topic_id}/subscriptions",
            json={
                "url": webhook_url,
                "secret": self.webhook_secret,
                "headers": {},
                "enabled": True
            },
            timeout=30)
        response.raise_for_status()
    
    async def _run_plugin(self,
                          plugin_id: str,
                          task_params: Dict[str, Any],
                          topic_id: str,
                          run_mode: Literal["once","recurring"]="once",
                          interval: float=300):
        """运行插件（通过创建一次性任务）"""
        response = await async_request(
            self.http_client,
            "post",
            f"{self.base_url}/api/v1/tasks",
            json={
                "plugin_id": plugin_id,
                "run_mode": run_mode,
                "params": task_params,
                "topic_id": topic_id,
                "interval": interval,
            },
            timeout=30)
        response.raise_for_status()
    
    # 新增：运行并持续监听结果（支持多次事件）
    @asynccontextmanager
    async def run_plugin_stream(
        self,
        plugin_id: str,
        run_mode: Literal["once","recurring"]="recurring",
        interval: float=300,
        buffer_size: int=100,
        task_params: TaskParams = TaskParams(),
        service_params: ServiceParams = ServiceParams(),
        **kwargs,
    ):
        """启动插件并持续监听其在所属topic中的多次结果。
        用法:
            async with client.run_plugin_stream("foo", {...}) as stream:
                async for event in stream:
                    ... # 处理每个事件
        返回的 event 结构: {"event_id", "topic_id", "plugin_id", "payload"}
        """
        params = {
            **task_params.__dict__,
            **service_params.__dict__,
            **kwargs,
        }
        await self._test_health()
        # 准备topic与订阅
        topic_id = f"stream-{uuid.uuid4()}"
        await self._create_topic(topic_id, f"Stream for {plugin_id}")
        webhook_url = f"http://{self.webhook_host}:{self.webhook_port}/webhook"
        await self._create_subscription(topic_id, webhook_url)

        # 注册监听队列
        q: asyncio.Queue = asyncio.Queue(maxsize=buffer_size)
        self._topic_listeners.setdefault(topic_id, []).append(q)

        stream = self._Stream(q, topic_id, self._topic_listeners)
        try:
            # 启动插件
            await self._run_plugin(plugin_id, params, topic_id, run_mode, interval)
            yield stream
        finally:
            await stream.close()

    # 新增：仅监听指定topic（不自动启动插件）
    @asynccontextmanager
    async def listen_topic(self, topic_id: str, buffer_size: int = 100):
        """监听已有topic上的事件（不创建任务）。
        用法:
            async with client.listen_topic(topic_id) as stream:
                async for event in stream:
                    ...
        """
        await self._test_health()
        # 假设服务端已存在该topic且订阅了本客户端webhook
        q: asyncio.Queue = asyncio.Queue(maxsize=buffer_size)
        self._topic_listeners.setdefault(topic_id, []).append(q)

        stream = self._Stream(q, topic_id, self._topic_listeners)
        try:
            yield stream
        finally:
            await stream.close()
    
    # 具体的RPC方法
    async def chat_with_yuanbao(
        self,
        ask_question: str,
        conversation_id: str=None,
        rpc_timeout_sec=30,
        task_params: TaskParams=TaskParams(),
        service_params: ServiceParams=ServiceParams()) -> Dict[str, Any]:
        """与AI元宝聊天"""
        params = {
            "ask_question": ask_question,
            "conversation_id": conversation_id,
            **task_params.__dict__,
            **service_params.__dict__,
        }
        async with self._rpc_call("yuanbao_chat", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    @asynccontextmanager
    async def chat_with_yuanbao_stream(
        self,
        ask_question: str,
        conversation_id: str = None,
        run_mode: Literal["once", "recurring"] = "recurring",
        interval: float = 300,
        buffer_size: int = 100,
        task_params: TaskParams = TaskParams(),
        service_params: ServiceParams = ServiceParams(),
    ):
        async with self.run_plugin_stream(
            plugin_id="yuanbao_chat",
            ask_question=ask_question,
            conversation_id=conversation_id,
            run_mode=run_mode,
            interval=interval,
            buffer_size=buffer_size,
            task_params=task_params,
            service_params=service_params,
        ) as stream:
            yield stream

    async def get_favorite_notes_brief_from_xhs(
        self,
        storage_data: str,
        rpc_timeout_sec=30,
        task_params: TaskParams = TaskParams(),
        service_params: ServiceParams = ServiceParams(),
        sync_params: SyncParams = SyncParams(),
    ) -> Dict[str, Any]:
        """从小红书获取笔记摘要"""
        params = {
            "storage_data": storage_data,
            **task_params.__dict__,
            **service_params.__dict__,
            **sync_params.__dict__,
        }
        
        async with self._rpc_call("xiaohongshu_favorites_brief", params, timeout_sec=rpc_timeout_sec) as result:
            return result
    
    async def get_notes_details_from_xhs(
        self,
        brief_data,
        wait_time_sec: int = 10,
        rpc_timeout_sec=30,
        task_params: TaskParams = TaskParams(),
        service_params: ServiceParams = ServiceParams()
    ) -> Dict[str, Any]:
        """从小红书获取笔记详情"""
        params = {
            "brief_data": brief_data,
            "wait_time_sec": wait_time_sec,
            **task_params.__dict__,
            **service_params.__dict__,
        }
        
        async with self._rpc_call("xiaohongshu_details", params, timeout_sec=rpc_timeout_sec) as result:
            return result
    
    async def search_notes_from_xhs(
        self, 
        keywords: List[str],
        rpc_timeout_sec=30,
        task_params: TaskParams = TaskParams(),
        service_params: ServiceParams = ServiceParams()
    ) -> Dict[str, Any]:
        """从小红书搜索笔记"""
        params = {
            "search_keywords": keywords,
            **task_params.__dict__,
            **service_params.__dict__,
        }
        
        async with self._rpc_call("xiaohongshu_search", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    async def get_collection_list_from_zhihu(
        self,
        user_id: Optional[str]=None,
        rpc_timeout_sec=30,
        task_params: TaskParams=TaskParams(),
        service_params: ServiceParams=ServiceParams()) -> Dict[str, Any]:
        """与AI元宝聊天"""
        params = {
            "user_id": user_id,
            **task_params.__dict__,
            **service_params.__dict__,
        }
        async with self._rpc_call("zhihu_collection_list", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    async def get_collection_list_from_bilibili(
        self,
        user_id: Optional[str]=None,
        rpc_timeout_sec=30,
        task_params: TaskParams=TaskParams(),
        service_params: ServiceParams=ServiceParams()) -> Dict[str, Any]:
        """与AI元宝聊天"""
        params = {
            "user_id": user_id,
            **task_params.__dict__,
            **service_params.__dict__,
        }
        async with self._rpc_call("bilibili_collection_list", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    async def get_collection_list_videos_from_bilibili(
        self,
        collection_id: str,
        user_id: Optional[str]=None,
        rpc_timeout_sec=30,
        task_params: TaskParams=TaskParams(),
        service_params: ServiceParams=ServiceParams()) -> Dict[str, Any]:
        """与AI元宝聊天"""
        params = {
            "user_id": user_id,
            "collection_id": collection_id,
            **task_params.__dict__,
            **service_params.__dict__,
        }
        async with self._rpc_call("bilibili_collection_videos", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    async def get_video_details_from_bilibili(
        self,
        bvid: str,
        rpc_timeout_sec=30,
        task_params: TaskParams=TaskParams(),
        service_params: ServiceParams=ServiceParams()) -> Dict[str, Any]:
        """与AI元宝聊天"""
        params = {
            "bvid": bvid,
            **task_params.__dict__,
            **service_params.__dict__,
        }
        async with self._rpc_call("bilibili_video_details", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    async def call_paddle_ocr(
        self,
        image_path_abs_path: str,
        lang: str = "ch",
        include_text: bool = True,
        need_merge_lines: bool = True,
        include_boxes: bool = False,
        include_confidence: bool = True,
        include_layout: bool = False,
        include_table: bool = False,
        include_raw_image: bool = True,
        rpc_timeout_sec=30,
        task_params: TaskParams = TaskParams(),
    ) -> Dict[str, Any]:
        """调用Paddle OCR"""
        params = {
            "lang": lang,
            "image_path_abs_path": image_path_abs_path,
            "include_text": include_text,
            "need_merge_lines": need_merge_lines,
            "include_boxes": include_boxes,
            "include_confidence": include_confidence,
            "include_layout": include_layout,
            "include_table": include_table,
            "include_raw_image": include_raw_image,
            **task_params.__dict__,
        }

        async with self._rpc_call("paddle_ocr", params, timeout_sec=rpc_timeout_sec) as result:
            return result

    # 通用插件调用方法
    async def call_plugin(
        self, 
        plugin_id: str,
        rpc_timeout_sec=30,
        task_params: TaskParams = TaskParams(),
        service_params: ServiceParams = ServiceParams(),
        **kwargs
    ) -> Dict[str, Any]:
        """通用插件调用方法"""
        params = {
            **task_params.__dict__,
            **service_params.__dict__,
            **kwargs,
        }
        async with self._rpc_call(plugin_id, params, timeout_sec=rpc_timeout_sec) as result:
            return result


# 便捷的同步包装器
class EAIRPCClientSync:
    """同步版本的RPC客户端"""
    
    def __init__(self, *args, **kwargs):
        self._client = EAIRPCClient(*args, **kwargs)
        self._loop = None
    
    def _ensure_loop(self):
        if self._loop is None:
            # self._loop = asyncio.get_event_loop()
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
    
    def start(self):
        self._ensure_loop()
        return self._loop.run_until_complete(self._client.start())
    
    def stop(self):
        if self._loop:
            return self._loop.run_until_complete(self._client.stop())
    
    def chat_with_yuanbao(self, message: str, **kwargs) -> Dict[str, Any]:
        self._ensure_loop()
        return self._loop.run_until_complete(
            self._client.chat_with_yuanbao(message, **kwargs)
        )
    
    def get_favorite_notes_brief_from_xhs(
        self, 
        keywords: List[str], 
        max_items: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        self._ensure_loop()
        return self._loop.run_until_complete(
            self._client.get_favorite_notes_brief_from_xhs(keywords, max_items, **kwargs)
        )
    
    def get_notes_details_from_xhs(
        self, 
        keywords: List[str], 
        max_items: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        self._ensure_loop()
        return self._loop.run_until_complete(
            self._client.get_notes_details_from_xhs(keywords, max_items, **kwargs)
        )
    
    def search_notes_from_xhs(
        self, 
        keywords: List[str], 
        max_items: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        self._ensure_loop()
        return self._loop.run_until_complete(
            self._client.search_notes_from_xhs(keywords, max_items, **kwargs)
        )
    
    def get_favorites_from_xhs(
        self, 
        max_items: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        self._ensure_loop()
        return self._loop.run_until_complete(
            self._client.get_favorites_from_xhs(max_items, **kwargs)
        )
    
    def call_plugin(
        self, 
        plugin_id: str, 
        params: Dict[str, Any],
        timeout: float = 300.0
    ) -> Dict[str, Any]:
        self._ensure_loop()
        return self._loop.run_until_complete(
            self._client.call_plugin(plugin_id, params, timeout)
        )