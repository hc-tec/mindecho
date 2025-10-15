from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.api import deps
from app.core.websocket_manager import manager
from app.services.listener_service import toggle_workshop_listening
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

# Websocket endpoint removed: frontend uses polling now

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

@router.get("/manage/{workshop_id}", response_model=WorkshopSchema)
async def get_workshop(workshop_id: str, db: AsyncSession = Depends(deps.get_db)):
    """Fetch a single workshop by its slug-like workshop_id."""
    row = (await db.execute(select(WorkshopModel).where(WorkshopModel.workshop_id == workshop_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Workshop not found")
    return _model_to_schema_dict(row)

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


class ToggleListeningPayload(BaseModel):
    enabled: bool
    workshop_name: Optional[str] = None


@router.post("/manage/{workshop_id}/toggle-listening")
async def toggle_listening(workshop_id: str, payload: ToggleListeningPayload, db: AsyncSession = Depends(deps.get_db)):
    """Enable or disable per-collection listening for a workshop.

    Accepts JSON body: {"enabled": bool, "workshop_name": str | null}

    If enabled, and a collection exists whose title equals workshop_id, start a stream for that collection_id.
    If disabled, stop the stream.
    """
    # Delegate to service for better testability & separation of concerns
    result = await toggle_workshop_listening(
        db, workshop_id=workshop_id, enabled=payload.enabled, workshop_name=payload.workshop_name
    )
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail="Workshop not found")
    return result


class PlatformBinding(BaseModel):
    platform: str
    collection_ids: List[int]


class PlatformBindingsUpdate(BaseModel):
    """Update platform bindings for a workshop.

    New structure:
    {
        "platform_bindings": [
            {"platform": "bilibili", "collection_ids": [1, 2, 3]},
            {"platform": "xiaohongshu", "collection_ids": [4, 5]}
        ]
    }
    """
    platform_bindings: List[PlatformBinding]


@router.put("/manage/{workshop_id}/platform-bindings")
async def update_platform_bindings(
    workshop_id: str,
    bindings: PlatformBindingsUpdate,
    db: AsyncSession = Depends(deps.get_db)
):
    """Update platform bindings for a workshop (multi-platform, multi-collection).

    This replaces the old single-binding approach with a flexible multi-platform structure.

    Example payload:
    {
        "platform_bindings": [
            {"platform": "bilibili", "collection_ids": [1, 2, 3]},
            {"platform": "xiaohongshu", "collection_ids": [4, 5]}
        ]
    }
    """
    row = (await db.execute(select(WorkshopModel).where(WorkshopModel.workshop_id == workshop_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Workshop not found")

    import json as _json
    cfg = {}
    if row.executor_config:
        try:
            cfg = _json.loads(row.executor_config) or {}
        except Exception:
            cfg = {}

    # Update platform_bindings
    cfg["platform_bindings"] = [
        {"platform": b.platform, "collection_ids": b.collection_ids}
        for b in bindings.platform_bindings
    ]

    # Remove legacy single binding if exists
    cfg.pop("binding_collection_id", None)

    row.executor_config = _json.dumps(cfg, ensure_ascii=False)
    db.add(row)
    await db.commit()

    return {
        "ok": True,
        "platform_bindings": cfg["platform_bindings"]
    }


@router.get("/manage/{workshop_id}/platform-bindings")
async def get_platform_bindings(workshop_id: str, db: AsyncSession = Depends(deps.get_db)):
    """Get current platform bindings for a workshop."""
    row = (await db.execute(select(WorkshopModel).where(WorkshopModel.workshop_id == workshop_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Workshop not found")

    import json as _json
    cfg = {}
    if row.executor_config:
        try:
            cfg = _json.loads(row.executor_config) or {}
        except Exception:
            cfg = {}

    return {
        "platform_bindings": cfg.get("platform_bindings", []),
        "listening_enabled": cfg.get("listening_enabled", False)
    }


# Legacy endpoint (kept for backward compatibility)
class ListeningBindingUpdate(BaseModel):
    collection_id: Optional[int] = None


@router.put("/manage/{workshop_id}/binding")
async def update_listening_binding(workshop_id: str, binding: ListeningBindingUpdate, db: AsyncSession = Depends(deps.get_db)):
    """[DEPRECATED] Bind or unbind a workshop to a single collection_id.

    Use /platform-bindings endpoint instead for multi-platform support.
    """
    row = (await db.execute(select(WorkshopModel).where(WorkshopModel.workshop_id == workshop_id))).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Workshop not found")
    import json as _json
    cfg = {}
    if row.executor_config:
        try:
            cfg = _json.loads(row.executor_config) or {}
        except Exception:
            cfg = {}
    if binding.collection_id is None:
        cfg.pop("binding_collection_id", None)
    else:
        cfg["binding_collection_id"] = int(binding.collection_id)
    row.executor_config = _json.dumps(cfg, ensure_ascii=False)
    db.add(row)
    await db.commit()
    return {"ok": True, "binding_collection_id": cfg.get("binding_collection_id")}
