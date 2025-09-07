import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_get_dashboard_data(client: AsyncClient):
    """
    Test fetching the main dashboard data.
    """
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 200
    
    data = response.json()
    
    # Check if the main keys are present
    expected_keys = [
        "overviewStats",
        "activityHeatmap",
        "pendingQueue",
        "workshopMatrix",
        "recentOutputs",
        "trendSpottingKeywords",
    ]
    for key in expected_keys:
        assert key in data

    # Check the structure of overviewStats
    assert "totalCollections" in data["overviewStats"]
    assert "totalResults" in data["overviewStats"]
    assert "platforms" in data["overviewStats"]
    
    # Check that other keys are lists (even if empty)
    assert isinstance(data["activityHeatmap"], list)
    assert isinstance(data["pendingQueue"], list)
    assert isinstance(data["workshopMatrix"], list)
    assert isinstance(data["recentOutputs"], list)
    assert isinstance(data["trendSpottingKeywords"], list)
