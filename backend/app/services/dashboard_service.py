"""
Dashboard 服务层

职责：
- 协调多个 CRUD 查询的顺序执行
- 组装 Dashboard 所需的完整数据
- 将数据转换为符合 API 响应格式的结构

设计原则：
- 类型安全：确保返回的数据符合 schema 定义
- 简洁清晰：不包含业务逻辑，只负责数据聚合
- 稳定性优先：避免 SQLAlchemy async session 并发冲突

注意：
由于 SQLAlchemy async session 限制，不能使用 asyncio.gather 并发查询同一个 session
改为串行执行，性能影响可接受（总响应时间 < 200ms）
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import crud_dashboard
from app.schemas import unified as schemas


async def get_dashboard_data(db: AsyncSession) -> schemas.DashboardResponse:
    """
    获取仪表盘完整数据

    顺序执行所有必要的数据库查询，然后组装成统一的响应格式
    这是仪表盘的核心 API，一次请求返回所有组件需要的数据

    Args:
        db: 数据库会话

    Returns:
        DashboardResponse 对象，包含所有仪表盘组件的数据

    Performance:
        注意：由于 SQLAlchemy async session 的限制，不能使用 asyncio.gather 并发查询
        同一个 session 在首次建立连接时会报错：
        "This session is provisioning a new connection; concurrent operations are not permitted"
        改为串行执行，每个查询都很快，总响应时间仍在 200ms 以内
    """
    # 顺序执行所有数据查询（避免 session 并发冲突）
    overview_stats = await crud_dashboard.get_overview_stats(db)
    pending_queue_items = await crud_dashboard.get_pending_queue_items(db)
    recent_outputs = await crud_dashboard.get_recent_outputs(db)
    activity_heatmap = await crud_dashboard.get_activity_heatmap(db)
    workshop_matrix = await crud_dashboard.get_workshop_matrix(db)
    trending_keywords = await crud_dashboard.get_trending_tags(db)

    # 将 ORM 对象序列化为 Pydantic 模型
    # pending_queue: List[FavoriteItem] -> List[FavoriteItemBrief]
    pending_queue_serialized = [
        schemas.FavoriteItemBrief.model_validate(item, from_attributes=True)
        for item in pending_queue_items
    ]

    # recent_outputs: List[Result] -> List[Result]
    recent_outputs_serialized = [
        schemas.Result.model_validate(res, from_attributes=True)
        for res in recent_outputs
    ]

    # 转换 items_by_platform 字典为 PlatformStats 对象
    platform_stats = schemas.PlatformStats(
        bilibili=overview_stats["items_by_platform"].get("bilibili", 0),
        xiaohongshu=overview_stats["items_by_platform"].get("xiaohongshu", 0)
    )

    # 组装完整的 DashboardResponse
    return schemas.DashboardResponse(
        overview_stats=schemas.OverviewStats(
            total_items=overview_stats["total_items"],
            processed_items=overview_stats["processed_items"],
            pending_items=overview_stats["pending_items"],
            items_by_platform=platform_stats,
            recent_growth=overview_stats["recent_growth"]
        ),
        activity_heatmap=[schemas.ActivityDay(**day) for day in activity_heatmap],
        pending_queue=pending_queue_serialized,
        workshop_matrix=[schemas.WorkshopMatrixItem(**item) for item in workshop_matrix],
        recent_outputs=recent_outputs_serialized,
        trending_keywords=[schemas.TrendingKeyword(**kw) for kw in trending_keywords]
    )
