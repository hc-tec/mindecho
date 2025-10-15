from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional

from app.api import deps
from app.services import dashboard_service

router = APIRouter()

# Define a placeholder response model for now
from pydantic import BaseModel

class DashboardData(BaseModel):
    overviewStats: Dict[str, Any]
    activityHeatmap: List[Dict[str, Any]]
    pendingQueue: List[Dict[str, Any]]
    workshopMatrix: List[Dict[str, Any]]
    recentOutputs: List[Dict[str, Any]]
    trendSpottingKeywords: List[Dict[str, Any]]


class ExecutorStatus(BaseModel):
    """Executor concurrency status."""
    executor_type: str
    concurrency_limit: Optional[int]  # None = unlimited
    description: str
    is_unlimited: bool
    # Note: active_tasks count requires runtime tracking (not implemented yet)


class TaskQueueStats(BaseModel):
    """Task queue statistics."""
    pending: int
    in_progress: int
    success: int
    failed: int
    total: int


class RecoveryStats(BaseModel):
    """Recovery statistics for incomplete items."""
    items_need_details: int  # Items missing details
    items_need_tasks: int  # Items with details but no task
    total_incomplete: int


class SystemMonitoringData(BaseModel):
    """System monitoring data for dashboard."""
    executors: List[ExecutorStatus]
    task_queue: TaskQueueStats
    recovery_stats: RecoveryStats


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Get all aggregated data needed to render the main dashboard.
    """
    dashboard_data = await dashboard_service.get_dashboard_data(db)
    return dashboard_data


@router.get("/dashboard/monitoring", response_model=SystemMonitoringData)
async def get_system_monitoring(
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Get system monitoring data including executor status, task queue, and recovery stats.

    This endpoint provides real-time insights into:
    - Executor concurrency limits and status
    - Task queue statistics (pending, in progress, completed, failed)
    - Items requiring recovery (incomplete processing)
    """
    from app.services.executors import executor_registry
    from app.db.models import Task as TaskModel, TaskStatus, FavoriteItem
    from sqlalchemy import select, func, and_, or_

    # Get executor statuses
    executors = []
    for executor_type, config in executor_registry._concurrency_configs.items():
        executors.append(
            ExecutorStatus(
                executor_type=executor_type,
                concurrency_limit=config.limit,
                description=config.description,
                is_unlimited=config.is_unlimited()
            )
        )

    # Get task queue statistics
    task_counts = await db.execute(
        select(
            TaskModel.status,
            func.count(TaskModel.id).label('count')
        ).group_by(TaskModel.status)
    )

    status_map = {row.status: row.count for row in task_counts}

    task_queue = TaskQueueStats(
        pending=status_map.get(TaskStatus.PENDING, 0),
        in_progress=status_map.get(TaskStatus.IN_PROGRESS, 0),
        success=status_map.get(TaskStatus.SUCCESS, 0),
        failed=status_map.get(TaskStatus.FAILURE, 0),
        total=sum(status_map.values())
    )

    # Get recovery statistics
    # Items needing details (no details and not exhausted attempts)
    items_need_details_count = await db.execute(
        select(func.count(FavoriteItem.id)).where(
            and_(
                # Bilibili items without details
                or_(
                    and_(
                        FavoriteItem.platform == "bilibili",
                        ~FavoriteItem.bilibili_video_details.has()
                    ),
                    # Xiaohongshu items without details
                    and_(
                        FavoriteItem.platform == "xiaohongshu",
                        or_(
                            ~FavoriteItem.xiaohongshu_note_details.has(),
                            FavoriteItem.xiaohongshu_note_details.has(
                                FavoriteItem.xiaohongshu_note_details.property.mapper.class_.desc == ""
                            )
                        )
                    )
                ),
                # Not exhausted retry attempts
                or_(
                    FavoriteItem.details_fetch_attempts == None,
                    FavoriteItem.details_fetch_attempts < 5
                )
            )
        )
    )
    items_need_details = items_need_details_count.scalar() or 0

    # Items with details but no unfinished task
    # (Simplified: just count items with details that have no tasks at all)
    items_with_details_no_task = await db.execute(
        select(func.count(FavoriteItem.id)).where(
            and_(
                # Has details
                or_(
                    FavoriteItem.bilibili_video_details.has(),
                    and_(
                        FavoriteItem.xiaohongshu_note_details.has(),
                        FavoriteItem.xiaohongshu_note_details.property.mapper.class_.desc != ""
                    )
                ),
                # No tasks
                ~FavoriteItem.tasks.any()
            )
        )
    )
    items_need_tasks = items_with_details_no_task.scalar() or 0

    recovery_stats = RecoveryStats(
        items_need_details=items_need_details,
        items_need_tasks=items_need_tasks,
        total_incomplete=items_need_details + items_need_tasks
    )

    return SystemMonitoringData(
        executors=executors,
        task_queue=task_queue,
        recovery_stats=recovery_stats
    )
