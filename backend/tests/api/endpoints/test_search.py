import pytest
from httpx import AsyncClient
from datetime import datetime

pytestmark = pytest.mark.asyncio

async def test_global_search(client: AsyncClient):
    """Test the global search functionality."""
    # Create some data to search for
    await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "search-item-1", "platform": "bilibili",
            "item_type": "video", "title": "A unique keyword",
            "intro": "Some content here.", "favorited_at": datetime.utcnow().isoformat()
        }
    )
    # Note: We can't easily test searching 'Result' content without
    # creating a result, which we did in test_results.py.
    # For a unit test, we focus on the search endpoint's direct responsibility.
    
    # Search for the unique keyword
    response = await client.get("/api/v1/search?q=unique keyword")
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["collections"]) == 1
    assert data["collections"][0]["title"] == "A unique keyword"
    assert len(data["results"]) == 0 # We didn't create a matching result
    
    # Search for something that doesn't exist
    response_no_match = await client.get("/api/v1/search?q=nonexistent")
    assert response_no_match.status_code == 200
    data_no_match = response_no_match.json()
    assert len(data_no_match["collections"]) == 0
    assert len(data_no_match["results"]) == 0
