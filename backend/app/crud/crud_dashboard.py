import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text, desc
from typing import Dict, Any, List

from app.db.models import FavoriteItem, Result, PlatformEnum, FavoriteItemStatus, Task, TaskStatus, Tag, item_tags

async def get_overview_stats(db: AsyncSession) -> Dict[str, Any]:
    """
    Fetches statistics for the overview dashboard widget.
    - Total number of collections (approximated by favorite items for now)
    - Total number of results (AI-generated content)
    - Count of items per platform
    """
    total_items_query = select(func.count(FavoriteItem.id))
    total_items_result = await db.execute(total_items_query)
    total_items = total_items_result.scalar_one()
    
    total_results_query = select(func.count(Result.id))
    total_results_result = await db.execute(total_results_query)
    total_results = total_results_result.scalar_one()

    platform_counts_query = select(FavoriteItem.platform, func.count(FavoriteItem.id)).group_by(FavoriteItem.platform)
    platform_counts_result = await db.execute(platform_counts_query)
    
    platforms = [
        {"name": platform.value, "count": count}
        for platform, count in platform_counts_result.all()
    ]

    return {
        # Note: Using item count as a proxy for collection count until full collection model is used
        "totalCollections": total_items,
        "totalResults": total_results,
        "platforms": platforms
    }

async def get_pending_queue_items(db: AsyncSession, *, limit: int = 10) -> List[FavoriteItem]:
    """
    Fetches the latest items with a 'pending' status for the dashboard's pending queue.
    """
    query = (
        select(FavoriteItem)
        .where(FavoriteItem.status == FavoriteItemStatus.PENDING)
        .order_by(FavoriteItem.favorited_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

async def get_recent_outputs(db: AsyncSession, *, limit: int = 5) -> List[Result]:
    """
    Fetches the most recently created AI-generated results.
    """
    query = (
        select(Result)
        .order_by(Result.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

async def get_activity_heatmap(db: AsyncSession, days: int = 30) -> List[Dict[str, Any]]:
    """
    Fetches the user's activity count (number of items favorited) for the last N days.
    """
    start_date = datetime.date.today() - datetime.timedelta(days=days)
    
    # This query counts items per day.
    # The date() function is specific to SQLite, use other functions for other DBs (e.g., DATE_TRUNC for PostgreSQL)
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
    
    # Format the data into the structure expected by the frontend
    heatmap_data = [{"date": row.date, "count": row.count} for row in result.all()]
    
    return heatmap_data

async def get_workshop_matrix(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Fetches statistics for the workshop matrix widget.
    - Total results per workshop
    - In-progress tasks per workshop
    """
    # This is a placeholder for where workshop definitions would come from.
    # In a real app, this might be its own database table.
    defined_workshops = {
        "summary-01": "精华摘要",
        "snapshot-insight": "快照洞察",
        "information-alchemy": "信息炼金术",
        "point-counterpoint": "观点对撞",
        "learning-tasks": "学习任务"
    }

    # Query 1: Get total result counts grouped by workshop_id
    total_results_query = (
        select(Result.workshop_id, func.count(Result.id).label("total"))
        .group_by(Result.workshop_id)
    )
    total_results_result = await db.execute(total_results_query)
    totals_map = {row.workshop_id: row.total for row in total_results_result.all()}

    # Query 2: Get in-progress task counts grouped by workshop_id
    in_progress_query = (
        select(Task.workshop_id, func.count(Task.id).label("in_progress"))
        .where(Task.status == TaskStatus.IN_PROGRESS)
        .group_by(Task.workshop_id)
    )
    in_progress_result = await db.execute(in_progress_query)
    in_progress_map = {row.workshop_id: row.in_progress for row in in_progress_result.all()}
    
    # Query 3: Get activity for the last 7 days
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
    
    activity_map = {ws_id: { (datetime.date.today() - datetime.timedelta(days=i)).isoformat(): 0 for i in range(7) } for ws_id in defined_workshops}
    for row in daily_activity_result.all():
        if row.workshop_id in activity_map:
            activity_map[row.workshop_id][row.date] = row.count

    # Combine the results
    matrix = []
    for ws_id, ws_name in defined_workshops.items():
        activity_last_7_days = [activity_map[ws_id][(datetime.date.today() - datetime.timedelta(days=i)).isoformat()] for i in range(6, -1, -1)]
        matrix.append({
            "id": ws_id,
            "name": ws_name,
            "total": totals_map.get(ws_id, 0),
            "inProgress": in_progress_map.get(ws_id, 0),
            "activityLast7Days": activity_last_7_days
        })

    return matrix

async def get_trending_tags(db: AsyncSession, *, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches the most frequently used tags to spot trends.
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
    return [{"keyword": row.name, "frequency": row.frequency} for row in result.all()]

