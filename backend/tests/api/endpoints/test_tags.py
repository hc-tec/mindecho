import pytest
from httpx import AsyncClient
from datetime import datetime

pytestmark = pytest.mark.asyncio

async def test_get_tags_with_counts(client: AsyncClient):
    """
    Test retrieving tags with their correct usage counts.
    """
    # First, create a couple of items and tag them to create data
    item1_resp = await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "tag-item-1", "platform": "bilibili", "item_type": "video",
            "title": "Tag Count Test 1", "favorited_at": datetime.utcnow().isoformat()
        }
    )
    item1_id = item1_resp.json()["id"]
    await client.post(f"/api/v1/collections/{item1_id}/tags", json={"tags": ["popular", "common"]})

    item2_resp = await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "tag-item-2", "platform": "bilibili", "item_type": "video",
            "title": "Tag Count Test 2", "favorited_at": datetime.utcnow().isoformat()
        }
    )
    item2_id = item2_resp.json()["id"]
    await client.post(f"/api/v1/collections/{item2_id}/tags", json={"tags": ["popular", "rare"]})

    # Now, get the tags with counts
    response = await client.get("/api/v1/tags")
    assert response.status_code == 200
    
    tags_data = response.json()
    
    # The list should be sorted by count descending
    assert len(tags_data) >= 3
    
    tag_map = {tag["name"]: tag["count"] for tag in tags_data}
    
    assert tag_map["popular"] == 2
    assert tag_map["common"] == 1
    assert tag_map["rare"] == 1
    
    # Verify sorting
    assert tags_data[0]["name"] == "popular"
