"""
Dashboard API 端点

提供仪表盘相关的 REST API：
- GET /dashboard - 获取完整的仪表盘数据
- GET /dashboard/monitoring - 获取系统监控数据（执行器状态、任务队列、恢复统计）

设计原则：
- 单一数据源：一个 endpoint 返回所有必要数据，减少客户端请求次数
- 类型安全：使用 Pydantic models 确保响应格式一致
- 性能优先：Service 层使用并发查询，响应时间优化
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.api import deps
from app.services import dashboard_service
from app.schemas import unified as schemas

router = APIRouter()


# ============================================================================
# System Monitoring Schemas
# ============================================================================

from pydantic import BaseModel


class ExecutorStatus(BaseModel):
    """执行器并发状态

    展示单个执行器的并发控制配置：
    - executor_type: 执行器类型（如 llm_chat）
    - concurrency_limit: 并发限制数（None 表示无限制）
    - description: 执行器描述
    - is_unlimited: 是否无限制
    """
    executor_type: str
    concurrency_limit: Optional[int]  # None = unlimited
    description: str
    is_unlimited: bool


class TaskQueueStats(BaseModel):
    """任务队列统计

    提供任务执行的整体概览：
    - pending: 等待执行的任务数
    - in_progress: 正在执行的任务数
    - success: 成功完成的任务数
    - failed: 失败的任务数
    - total: 所有任务总数
    """
    pending: int
    in_progress: int
    success: int
    failed: int
    total: int


class RecoveryStats(BaseModel):
    """恢复统计

    追踪未完成处理的项目，用于系统监控和恢复：
    - items_need_details: 缺少详情的项目数
    - items_need_tasks: 有详情但无任务的项目数
    - total_incomplete: 总共未完成的项目数
    """
    items_need_details: int  # Items missing details
    items_need_tasks: int  # Items with details but no task
    total_incomplete: int


class SystemMonitoringData(BaseModel):
    """系统监控数据

    聚合所有系统健康指标，用于 SystemMonitoring 组件
    """
    executors: List[ExecutorStatus]
    task_queue: TaskQueueStats
    recovery_stats: RecoveryStats


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/dashboard", response_model=schemas.DashboardResponse)
async def get_dashboard_data(
    db: AsyncSession = Depends(deps.get_db),
):
    """
    获取仪表盘完整数据

    返回仪表盘所有组件需要的数据，包括：
    - overview_stats: 总览统计（总收藏、已处理、待处理、平台分布、增长率）
    - activity_heatmap: 活动热力图（最近30天每天的收藏数）
    - pending_queue: 待处理队列（最近10个待处理项）
    - workshop_matrix: 工坊矩阵（每个工坊的统计和7天活动）
    - recent_outputs: 最近输出（最新5个 AI 生成结果）
    - trending_keywords: 趋势关键词（最热门的10个标签）

    Returns:
        DashboardResponse: 包含所有仪表盘数据的完整响应

    Performance:
        使用并发查询，典型响应时间 < 200ms
    """
    dashboard_data = await dashboard_service.get_dashboard_data(db)
    return dashboard_data


@router.get("/dashboard/monitoring", response_model=SystemMonitoringData)
async def get_system_monitoring(
    db: AsyncSession = Depends(deps.get_db),
):
    """
    获取系统监控数据

    提供系统运行状态的实时洞察：
    - 执行器并发限制和状态
    - 任务队列统计（pending, in progress, completed, failed）
    - 需要恢复的未完成项目数量

    用于 SystemMonitoring 组件，帮助用户了解系统健康状况

    Returns:
        SystemMonitoringData: 系统监控数据

    Note:
        执行器的 active_tasks 计数需要运行时追踪（未实现）
        当前只返回配置的并发限制，不返回实际活跃任务数
    """
    from app.services.executors import executor_registry
    from app.db.models import Task as TaskModel, TaskStatus, FavoriteItem
    from sqlalchemy import select, func, and_, or_

    # 1. 获取所有执行器的状态
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

    # 2. 获取任务队列统计
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

    # 3. 获取恢复统计

    # 3a. 需要获取详情的项目数（无详情且未超过重试次数）
    items_need_details_count = await db.execute(
        select(func.count(FavoriteItem.id)).where(
            and_(
                # Bilibili 或 Xiaohongshu 无详情
                or_(
                    and_(
                        FavoriteItem.platform == "bilibili",
                        ~FavoriteItem.bilibili_video_details.has()
                    ),
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
                # 未超过重试次数限制（5次）
                or_(
                    FavoriteItem.details_fetch_attempts == None,
                    FavoriteItem.details_fetch_attempts < 5
                )
            )
        )
    )
    items_need_details = items_need_details_count.scalar() or 0

    # 3b. 有详情但无任务的项目数
    items_with_details_no_task = await db.execute(
        select(func.count(FavoriteItem.id)).where(
            and_(
                # 有详情
                or_(
                    FavoriteItem.bilibili_video_details.has(),
                    and_(
                        FavoriteItem.xiaohongshu_note_details.has(),
                        FavoriteItem.xiaohongshu_note_details.property.mapper.class_.desc != ""
                    )
                ),
                # 无任何任务
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
