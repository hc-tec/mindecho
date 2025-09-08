from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.services.stream_manager import stream_manager
from app.core.websocket_manager import manager as websocket_manager


router = APIRouter()


@router.get("/streams")
async def list_streams():
    return {"running": stream_manager.list_streams()}


@router.post("/streams/start")
async def start_stream(
    plugin_id: str,
    stream_id: Optional[str] = None,
    group: Optional[str] = Query(default=None, description="Broadcast group name; if empty, send to stream_id only"),
    run_mode: str = Query(default="recurring"),
    interval: float = Query(default=300.0, ge=0.1, le=86400),
    buffer_size: int = Query(default=100, ge=1, le=10000),
    params: Optional[Dict[str, Any]] = None,
):
    sid = stream_id or plugin_id
    stream_manager.start_stream(
        stream_id=sid,
        plugin_id=plugin_id,
        group=group,
        run_mode=run_mode,
        interval=interval,
        buffer_size=buffer_size,
        params=params or {},
    )
    return {"stream_id": sid}


@router.post("/streams/{stream_id}/stop")
async def stop_stream(stream_id: str):
    ok = stream_manager.stop_stream(stream_id)
    if not ok:
        raise HTTPException(status_code=404, detail="stream not found")
    return {"ok": True}


@router.websocket("/ws/streams/{stream_id}")
async def ws_stream(ws: WebSocket, stream_id: str, group: Optional[str] = None):
    await websocket_manager.connect(ws, task_id=stream_id)
    try:
        if group:
            websocket_manager.join_group(stream_id, group)
        while True:
            # optional client pings
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if group:
            websocket_manager.leave_group(stream_id, group)
        websocket_manager.disconnect(stream_id)


