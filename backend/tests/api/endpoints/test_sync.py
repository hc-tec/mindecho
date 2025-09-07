import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_rpc_client(monkeypatch):
    """Fixture to mock the EAIRPCClient."""
    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()
    
    mock_client.get_collection_list_from_bilibili = AsyncMock(return_value={
        "success": True,
        "data": [{
            "id": "12345", "title": "Test Collection", "item_count": 1,
            "creator": {"user_id": "uid-1", "username": "user1", "avatar": ""}
        }]
    })
    mock_client.get_collection_list_videos_from_bilibili = AsyncMock(return_value={
        "success": True,
        "data": [{
            "bvid": "BV123", "title": "Test Video", "fav_time": "1672531200",
            "creator": {"user_id": "uid-2", "username": "user2", "avatar": ""}
        }]
    })
    mock_client.get_video_details_from_bilibili = AsyncMock(return_value={
        "success": True,
        "data": {
            "bvid": "BV123", "title": "Test Video Full", "pubdate": "1672531100",
            "stat": {}, "tags": [{"tag_name": "test"}],
            "creator": {"user_id": "uid-2", "username": "user2", "avatar": ""}
        }
    })

    monkeypatch.setattr("app.services.favorites_service.EAIRPCClient", lambda *args, **kwargs: mock_client)
    return mock_client

async def test_sync_collections(client: AsyncClient, mock_rpc_client):
    """Test syncing Bilibili collections."""
    response = await client.post("/api/v1/sync/bilibili/collections", json={"max_collections": 1})
    assert response.status_code == 200
    assert response.json()["synced_collections_count"] == 1
    assert response.json()["collections"][0]["platform_collection_id"] == "12345"
    mock_rpc_client.get_collection_list_from_bilibili.assert_called_once()

async def test_sync_videos_in_collection(client: AsyncClient, mock_rpc_client):
    """Test syncing videos within a specific collection."""
    # First, sync the collection to ensure it exists
    await client.post("/api/v1/sync/bilibili/collections", json={})
    
    response = await client.post("/api/v1/sync/bilibili/collections/12345/videos", json={"max_videos": 1})
    assert response.status_code == 200
    assert response.json()["synced_videos_count"] == 1
    assert response.json()["videos"][0]["platform_item_id"] == "BV123"
    mock_rpc_client.get_collection_list_videos_from_bilibili.assert_called_once()

async def test_sync_video_details(client: AsyncClient, mock_rpc_client):
    """Test syncing full details for a video."""
    # First, sync the collection and the video brief
    await client.post("/api/v1/sync/bilibili/collections", json={})
    await client.post("/api/v1/sync/bilibili/collections/12345/videos", json={})

    response = await client.post("/api/v1/sync/bilibili/videos/details", json={"bvids": ["BV123"]})
    assert response.status_code == 200
    assert response.json()["updated_videos_count"] == 1
    assert response.json()["videos"][0]["title"] == "Test Video Full"
    mock_rpc_client.get_video_details_from_bilibili.assert_called_once()
