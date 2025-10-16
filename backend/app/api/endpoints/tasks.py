from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy import func, select, delete
from sqlalchemy.orm import selectinload

from app.api import deps
from app.db.models import Task as TaskModel
from app.schemas.unified import Task
from app.db.models import TaskStatus

router = APIRouter()

class GlobalTaskStatus(BaseModel):
    in_progress: int
    pending: int
    total: int

@router.get("/status", response_model=GlobalTaskStatus)
async def get_global_task_status(db: AsyncSession = Depends(deps.get_db)):
    """
    Get a global overview of task statuses.
    """
    pending_query = select(func.count(TaskModel.id)).where(TaskModel.status == TaskStatus.PENDING)
    in_progress_query = select(func.count(TaskModel.id)).where(TaskModel.status == TaskStatus.IN_PROGRESS)
    pending_result = await db.execute(pending_query)
    in_progress_result = await db.execute(in_progress_query)
    pending = pending_result.scalar_one()
    in_progress = in_progress_result.scalar_one()
    return {"in_progress": in_progress, "pending": pending, "total": in_progress + pending}


class TaskListResponse(BaseModel):
    total: int
    items: List[Task]


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    db: AsyncSession = Depends(deps.get_db),
    status: Optional[str] = None,
    page: int = 1,
    size: int = 20,
):
    """Paginated task list for polling on the frontend."""
    query = select(TaskModel).order_by(TaskModel.id.desc())
    if status in {"pending", "in_progress", "success", "failure"}:
        query = query.where(TaskModel.status == status)
    total = (await db.execute(select(func.count(TaskModel.id)))).scalar_one()
    result = await db.execute(query.offset((page - 1) * size).limit(size))
    tasks = result.scalars().all()
    return {"total": total, "items": tasks}

@router.get("/{task_id}", response_model=Task)
async def read_task_status(
    *,
    db: AsyncSession = Depends(deps.get_db),
    task_id: int,
):
    """
    Retrieve the current status of a specific background task.
    """
    query = select(TaskModel).options(selectinload(TaskModel.result)).where(TaskModel.id == task_id)
    result = await db.execute(query)
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/clear-completed", status_code=status.HTTP_204_NO_CONTENT)
async def clear_completed_tasks(db: AsyncSession = Depends(deps.get_db)):
    """
    Delete all tasks that have a 'success' or 'failure' status.
    """
    query = delete(TaskModel).where(
        TaskModel.status.in_([TaskStatus.SUCCESS, TaskStatus.FAILURE])
    )
    await db.execute(query)
    await db.commit()
    return

@router.post("/cleanup-stale")
async def cleanup_stale_tasks(db: AsyncSession = Depends(deps.get_db)):
    """
    Mark IN_PROGRESS tasks older than 1 hour as FAILURE.
    This prevents tasks from getting stuck indefinitely.
    """
    from datetime import datetime, timedelta

    stale_cutoff = datetime.utcnow() - timedelta(hours=1)
    stale_tasks_query = select(TaskModel).where(
        TaskModel.status == TaskStatus.IN_PROGRESS,
        TaskModel.created_at < stale_cutoff
    )
    stale_tasks_result = await db.execute(stale_tasks_query)
    stale_tasks = stale_tasks_result.scalars().all()

    count = len(stale_tasks)
    for task in stale_tasks:
        task.status = TaskStatus.FAILURE
        db.add(task)

    await db.commit()
    return {"cleaned": count, "message": f"Marked {count} stale tasks as FAILURE"}
