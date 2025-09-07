from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api import deps
from app.core.websocket_manager import manager
from app.services import workshop_service 

router = APIRouter()

class WorkshopExecutionRequest(BaseModel):
    collection_id: int

class WorkshopExecutionResponse(BaseModel):
    message: str
    task_id: int

class WorkshopInfo(BaseModel):
    id: str
    name: str

@router.get("", response_model=List[WorkshopInfo])
async def get_available_workshops():
    """
    Get a list of all available AI workshops.
    """
    # This list is static for now, but could come from a database in the future.
    defined_workshops = {
        "summary-01": "精华摘要",
        "snapshot-insight": "快照洞察",
        "information-alchemy": "信息炼金术",
        "point-counterpoint": "观点对撞",
        "learning-tasks": "学习任务"
    }
    return [{"id": ws_id, "name": ws_name} for ws_id, ws_name in defined_workshops.items()]

@router.post("/{workshop_id}/execute", response_model=WorkshopExecutionResponse, status_code=202)
async def execute_workshop(
    workshop_id: str,
    request: WorkshopExecutionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Execute an AI workshop task on a given collection.
    This starts a background task and returns a task_id for tracking.
    """
    task = await workshop_service.start_workshop_task(
        db, workshop_id=workshop_id, collection_id=request.collection_id
    )
    background_tasks.add_task(workshop_service.run_workshop_task, db=db, task_id=task.id)
    return {"message": "Workshop task started.", "task_id": task.id}

@router.websocket("/ws/{task_id}")
async def workshop_websocket(websocket: WebSocket, task_id: str):
    await manager.connect(websocket, task_id)
    try:
        while True:
            # The websocket will simply listen for messages from the server.
            # We can add logic here if client-to-server messages are needed.
            await websocket.receive_text() 
    except WebSocketDisconnect:
        manager.disconnect(task_id)
        print(f"WebSocket disconnected for task_id: {task_id}")
