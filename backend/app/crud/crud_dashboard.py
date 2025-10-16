"""
Dashboard 数据访问层

职责：
- 从数据库查询 Dashboard 所需的统计数据
- 提供高性能的聚合查询
- 返回结构化数据供 Service 层使用

设计原则：
- 单一职责：每个函数只做一件事
- 性能优先：尽量减少数据库查询次数
- 类型安全：使用明确的类型注解
"""

import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text, desc, and_
from typing import Dict, Any, List

from app.db.models import (
    FavoriteItem, Result, PlatformEnum, FavoriteItemStatus,
    Task, TaskStatus, Tag, item_tags
)


async def get_overview_stats(db: AsyncSession) -> Dict[str, Any]:
    """
    获取仪表盘总览统计数据

    统计指标：
    - total_items: 总收藏数（所有 FavoriteItem）
    - processed_items: 已处理数（有成功 Result 的项）
    - pending_items: 待处理数（status = PENDING 的项）
    - items_by_platform: 按平台分布 {"bilibili": x, "xiaohongshu": y}
    - recent_growth: 最近30天相比之前30天的增长百分比

    Returns:
        符合 OverviewStats schema 的字典
    """
    # 1. 总收藏数
    total_items_query = select(func.count(FavoriteItem.id))
    total_items_result = await db.execute(total_items_query)
    total_items = total_items_result.scalar_one()

    # 2. 已处理数（有成功的 Result）
    # 方案：统计有至少一个 Result 的 FavoriteItem 数量
    processed_items_query = select(func.count(func.distinct(Result.favorite_item_id)))
    processed_items_result = await db.execute(processed_items_query)
    processed_items = processed_items_result.scalar_one()

    # 3. 待处理数（status = PENDING）
    pending_items_query = select(func.count(FavoriteItem.id)).where(
        FavoriteItem.status == FavoriteItemStatus.PENDING
    )
    pending_items_result = await db.execute(pending_items_query)
    pending_items = pending_items_result.scalar_one()

    # 4. 按平台分布
    platform_counts_query = select(
        FavoriteItem.platform,
        func.count(FavoriteItem.id)
    ).group_by(FavoriteItem.platform)
    platform_counts_result = await db.execute(platform_counts_query)

    # 转换为固定格式的字典
    items_by_platform = {"bilibili": 0, "xiaohongshu": 0}
    for platform, count in platform_counts_result.all():
        platform_name = platform.value if isinstance(platform, PlatformEnum) else platform
        if platform_name in items_by_platform:
            items_by_platform[platform_name] = count

    # 5. 最近30天增长率
    # 计算最近30天和之前30天的项目数，得出增长百分比
    today = datetime.date.today()
    thirty_days_ago = today - datetime.timedelta(days=30)
    sixty_days_ago = today - datetime.timedelta(days=60)

    # 最近30天的数量
    recent_count_query = select(func.count(FavoriteItem.id)).where(
        FavoriteItem.favorited_at >= thirty_days_ago
    )
    recent_count_result = await db.execute(recent_count_query)
    recent_count = recent_count_result.scalar_one()

    # 之前30天的数量（30-60天前）
    previous_count_query = select(func.count(FavoriteItem.id)).where(
        and_(
            FavoriteItem.favorited_at >= sixty_days_ago,
            FavoriteItem.favorited_at < thirty_days_ago
        )
    )
    previous_count_result = await db.execute(previous_count_query)
    previous_count = previous_count_result.scalar_one()

    # 计算增长率（避免除以零）
    if previous_count > 0:
        recent_growth = ((recent_count - previous_count) / previous_count) * 100
    else:
        recent_growth = 100.0 if recent_count > 0 else 0.0

    return {
        "total_items": total_items,
        "processed_items": processed_items,
        "pending_items": pending_items,
        "items_by_platform": items_by_platform,
        "recent_growth": round(recent_growth, 1)  # 保留一位小数
    }


async def get_pending_queue_items(db: AsyncSession, *, limit: int = 10) -> List[FavoriteItem]:
    """
    获取待处理队列中的项目

    返回最近收藏的待处理项目，用于仪表盘的待处理队列组件

    Args:
        db: 数据库会话
        limit: 返回数量限制，默认10条

    Returns:
        FavoriteItem 对象列表，按 favorited_at 降序排列
    """
    query = (
        select(FavoriteItem)
        .where(FavoriteItem.status == FavoriteItemStatus.PENDING)
        .order_by(FavoriteItem.favorited_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recent_outputs(db: AsyncSession, *, limit: int = 5) -> List[Result]:
    """
    获取最近的 AI 输出结果

    返回最新生成的 Result，用于仪表盘的最近输出组件

    Args:
        db: 数据库会话
        limit: 返回数量限制，默认5条

    Returns:
        Result 对象列表，按 created_at 降序排列
    """
    query = (
        select(Result)
        .order_by(Result.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_activity_heatmap(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
    """
    获取用户活动热力图数据

    统计最近 N 天每天的收藏数量，用于生成活动热力图可视化

    Args:
        db: 数据库会话
        days: 统计天数，默认30天

    Returns:
        列表，每项包含 {"date": "2024-01-01", "count": 10}
        按日期升序排列（从旧到新）

    Note:
        使用 SQLite 的 date() 函数，如果切换到 PostgreSQL 需改用 DATE_TRUNC
    """
    start_date = datetime.date.today() - datetime.timedelta(days=days)

    # SQLite 专用 date() 函数
    query = (
        select(
            func.date(FavoriteItem.favorited_at).label("date"),
            func.count(FavoriteItem.id).label("count")
        )
        .where(FavoriteItem.favorited_at >= start_date)
        .group_by(text("date"))
        .order_by(text("date"))
    )

    result = await db.execute(query)

    # 格式化为前端需要的结构
    heatmap_data = [
        {"date": row.date, "count": row.count}
        for row in result.all()
    ]

    return heatmap_data


async def get_workshop_matrix(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    获取工坊矩阵数据

    为每个工坊统计：
    - id: workshop_id
    - name: 工坊名称
    - total: 历史总输出数（Result 总数）
    - in_progress: 当前进行中的任务数
    - activity_last_7_days: 最近7天每天的任务创建数（数组，从旧到新）

    Returns:
        工坊统计数据列表，每项符合 WorkshopMatrixItem schema

    Note:
        这里硬编码了工坊列表，未来应该从 workshops 表动态获取
    """
    # TODO: 从 workshops 表动态获取工坊列表
    # 当前暂时硬编码常用工坊
    defined_workshops = {
        "summary-01": "精华摘要",
        "snapshot-insight": "快照洞察",
        "information-alchemy": "信息炼金术",
        "point-counterpoint": "观点对撞",
        "learning-tasks": "学习任务"
    }

    # Query 1: 统计每个工坊的历史总输出数（Result 总数）
    total_results_query = (
        select(Result.workshop_id, func.count(Result.id).label("total"))
        .group_by(Result.workshop_id)
    )
    total_results_result = await db.execute(total_results_query)
    totals_map = {row.workshop_id: row.total for row in total_results_result.all()}

    # Query 2: 统计每个工坊当前进行中的任务数
    in_progress_query = (
        select(Task.workshop_id, func.count(Task.id).label("in_progress"))
        .where(Task.status == TaskStatus.IN_PROGRESS)
        .group_by(Task.workshop_id)
    )
    in_progress_result = await db.execute(in_progress_query)
    in_progress_map = {row.workshop_id: row.in_progress for row in in_progress_result.all()}

    # Query 3: 统计最近7天每天的任务创建数
    seven_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    daily_activity_query = (
        select(
            Task.workshop_id,
            func.date(Task.created_at).label("date"),
            func.count(Task.id).label("count")
        )
        .where(Task.created_at >= seven_days_ago)
        .group_by(Task.workshop_id, func.date(Task.created_at))
    )
    daily_activity_result = await db.execute(daily_activity_query)

    # 初始化每个工坊最近7天的活动数据（全部为0）
    activity_map = {
        ws_id: {
            (datetime.date.today() - datetime.timedelta(days=i)).isoformat(): 0
            for i in range(7)
        }
        for ws_id in defined_workshops
    }

    # 填充实际数据
    for row in daily_activity_result.all():
        if row.workshop_id in activity_map:
            activity_map[row.workshop_id][row.date] = row.count

    # 组装最终数据
    matrix = []
    for ws_id, ws_name in defined_workshops.items():
        # 从7天前到今天的活动数（数组格式）
        activity_last_7_days = [
            activity_map[ws_id][(datetime.date.today() - datetime.timedelta(days=i)).isoformat()]
            for i in range(6, -1, -1)  # 倒序：6天前 -> 今天
        ]

        matrix.append({
            "id": ws_id,
            "name": ws_name,
            "total": totals_map.get(ws_id, 0),
            "in_progress": in_progress_map.get(ws_id, 0),
            "activity_last_7_days": activity_last_7_days
        })

    return matrix


async def get_trending_tags(db: AsyncSession, *, limit: int = 10) -> List[Dict[str, Any]]:
    """
    获取趋势标签/关键词

    统计最频繁使用的标签，用于发现用户收藏内容的趋势和主题

    Args:
        db: 数据库会话
        limit: 返回数量限制，默认10条

    Returns:
        列表，每项包含 {"keyword": "标签名", "frequency": 频次}
        按 frequency 降序排列

    Note:
        标签来自 FavoriteItem 的多对多关系表 item_tags
    """
    query = (
        select(
            Tag.name,
            func.count(item_tags.c.item_id).label("frequency")
        )
        .join(item_tags, Tag.id == item_tags.c.tag_id)
        .group_by(Tag.name)
        .order_by(desc("frequency"))
        .limit(limit)
    )
    result = await db.execute(query)

    return [
        {"keyword": row.name, "frequency": row.frequency}
        for row in result.all()
    ]
