from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.api import deps
from app.core.websocket_manager import manager
from app.services import workshop_service 

router = APIRouter()

class WorkshopExecutionRequest(BaseModel):
    collection_id: int
    prompt: Optional[str] = None
    llm_model: Optional[str] = None

class WorkshopExecutionResponse(BaseModel):
    message: str
    task_id: int

class WorkshopInfo(BaseModel):
    id: str
    name: str

@router.get("", response_model=List[WorkshopInfo])
async def get_available_workshops(db: AsyncSession = Depends(deps.get_db)):
    """
    Get a list of all available AI workshops.
    """
    from app.db.models import Workshop as WorkshopModel
    rows = (await db.execute(select(WorkshopModel))).scalars().all()
    return [{"id": r.workshop_id, "name": r.name} for r in rows]

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
        db, workshop_id=workshop_id, collection_id=request.collection_id, prompt=request.prompt, llm_model=request.llm_model
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

# --- Workshops CRUD ---
from app.schemas.unified import Workshop as WorkshopSchema, WorkshopCreate, WorkshopUpdate
from app.db.models import Workshop as WorkshopModel
import json

def _model_to_schema_dict(row: WorkshopModel) -> dict:
    return {
        "id": row.id,
        "workshop_id": row.workshop_id,
        "name": row.name,
        "description": row.description,
        "default_prompt": row.default_prompt,
        "default_model": row.default_model,
        "executor_type": row.executor_type,
        "executor_config": (json.loads(row.executor_config) if row.executor_config else None),
    }

@router.get("/manage", response_model=List[WorkshopSchema])
async def list_workshops(db: AsyncSession = Depends(deps.get_db)):
    rows = (await db.execute(select(WorkshopModel))).scalars().all()
    return [_model_to_schema_dict(r) for r in rows]

@router.post("/manage", response_model=WorkshopSchema)
async def create_workshop(payload: WorkshopCreate, db: AsyncSession = Depends(deps.get_db)):
    exists = (await db.execute(select(WorkshopModel).where(WorkshopModel.workshop_id == payload.workshop_id))).scalars().first()
    if exists:
        raise HTTPException(status_code=400, detail="workshop_id already exists")
    row = WorkshopModel(
        workshop_id=payload.workshop_id,
        name=payload.name,
        description=payload.description,
        default_prompt=payload.default_prompt,
        default_model=payload.default_model,
        executor_type=payload.executor_type,
        executor_config=json.dumps(payload.executor_config, ensure_ascii=False) if payload.executor_config is not None else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _model_to_schema_dict(row)

@router.put("/manage/{workshop_id}", response_model=WorkshopSchema)
async def update_workshop(workshop_id: str, payload: WorkshopUpdate, db: AsyncSession = Depends(deps.get_db)):
    row = (await db.execute(select(WorkshopModel).where(WorkshopModel.workshop_id == workshop_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Workshop not found")
    if payload.name is not None:
        row.name = payload.name
    if payload.description is not None:
        row.description = payload.description
    if payload.default_prompt is not None:
        row.default_prompt = payload.default_prompt
    if payload.default_model is not None:
        row.default_model = payload.default_model
    if payload.executor_type is not None:
        row.executor_type = payload.executor_type
    if payload.executor_config is not None:
        row.executor_config = json.dumps(payload.executor_config, ensure_ascii=False)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _model_to_schema_dict(row)

@router.delete("/manage/{workshop_id}")
async def delete_workshop(workshop_id: str, db: AsyncSession = Depends(deps.get_db)):
    row = (await db.execute(select(WorkshopModel).where(WorkshopModel.workshop_id == workshop_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Workshop not found")
    await db.delete(row)
    await db.commit()
    return {"ok": True}
