from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import asyncio

from app.crud import crud_dashboard
from app.schemas import unified as schemas

async def get_dashboard_data(db: AsyncSession) -> Dict[str, Any]:
    """
    Orchestrates fetching of all data required for the dashboard.
    """
    (
        overview_stats,
        pending_queue_items,
        recent_outputs,
        activity_heatmap,
        workshop_matrix,
        trending_keywords
    ) = await asyncio.gather(
        crud_dashboard.get_overview_stats(db),
        crud_dashboard.get_pending_queue_items(db),
        crud_dashboard.get_recent_outputs(db),
        crud_dashboard.get_activity_heatmap(db),
        crud_dashboard.get_workshop_matrix(db),
        crud_dashboard.get_trending_tags(db)
    )
    
    # Normalize ORM objects to plain dicts to satisfy response model
    pending_queue_serialized = [
        schemas.FavoriteItemBrief.model_validate(item, from_attributes=True).dict()
        for item in pending_queue_items
    ]

    recent_outputs_serialized = [
        schemas.Result.model_validate(res, from_attributes=True).dict()
        for res in recent_outputs
    ]

    dashboard_data = {
        "overviewStats": overview_stats,
        "activityHeatmap": activity_heatmap,
        "pendingQueue": pending_queue_serialized,
        "workshopMatrix": workshop_matrix,
        "recentOutputs": recent_outputs_serialized,
        "trendSpottingKeywords": trending_keywords
    }
    return dashboard_data
