from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Dict, Any
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
