from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

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


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data(
    db: AsyncSession = Depends(deps.get_db),
):
    """
    Get all aggregated data needed to render the main dashboard.
    """
    dashboard_data = await dashboard_service.get_dashboard_data(db)
    return dashboard_data
