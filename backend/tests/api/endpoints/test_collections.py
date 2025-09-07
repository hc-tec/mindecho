import pytest
from httpx import AsyncClient
from datetime import datetime

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_create_and_read_collection(client: AsyncClient):
    """
    Test creating a collection and then reading it back.
    """
    create_data = {
        "platform_item_id": "manual-123",
        "platform": "xiaohongshu",
        "item_type": "note",
        "title": "My First Manual Note",
        "intro": "This is a test note.",
        "favorited_at": datetime.utcnow().isoformat()
    }
    
    # Create
    response_create = await client.post("/api/v1/collections", json=create_data)
    assert response_create.status_code == 201
    created_data = response_create.json()
    assert created_data["title"] == create_data["title"]
    assert created_data["id"] is not None
    
    # Read
    collection_id = created_data["id"]
    response_read = await client.get(f"/api/v1/collections/{collection_id}")
    assert response_read.status_code == 200
    read_data = response_read.json()
    assert read_data["id"] == collection_id
    assert read_data["title"] == create_data["title"]


async def test_update_collection(client: AsyncClient):
    """
    Test updating a collection's title.
    """
    # First, create a collection to update
    create_data = {
        "platform_item_id": "manual-456", "platform": "xiaohongshu",
        "item_type": "note", "title": "Original Title",
        "favorited_at": datetime.utcnow().isoformat()
    }
    response_create = await client.post("/api/v1/collections", json=create_data)
    collection_id = response_create.json()["id"]

    # Update
    update_data = {"title": "Updated Title", "status": "processed"}
    response_update = await client.put(f"/api/v1/collections/{collection_id}", json=update_data)
    assert response_update.status_code == 200
    updated_data = response_update.json()
    assert updated_data["title"] == "Updated Title"
    assert updated_data["status"] == "processed"


async def test_manage_tags(client: AsyncClient):
    """
    Test adding and removing tags from a collection.
    """
    # Create a collection
    create_data = {
        "platform_item_id": "manual-789", "platform": "xiaohongshu",
        "item_type": "note", "title": "Tag Test Note",
        "favorited_at": datetime.utcnow().isoformat()
    }
    response_create = await client.post("/api/v1/collections", json=create_data)
    collection_id = response_create.json()["id"]

    # Add tags
    add_tags_data = {"tags": ["testing", "python"]}
    response_add_tags = await client.post(f"/api/v1/collections/{collection_id}/tags", json=add_tags_data)
    assert response_add_tags.status_code == 200
    data_with_tags = response_add_tags.json()
    assert len(data_with_tags["tags"]) == 2
    tag_names = {tag["name"] for tag in data_with_tags["tags"]}
    assert "testing" in tag_names and "python" in tag_names

    # Remove a tag
    remove_tags_data = {"tags": ["testing"]}
    response_remove_tags = await client.request("DELETE", f"/api/v1/collections/{collection_id}/tags", json=remove_tags_data)
    assert response_remove_tags.status_code == 200
    data_after_remove = response_remove_tags.json()
    assert len(data_after_remove["tags"]) == 1
    assert data_after_remove["tags"][0]["name"] == "python"


async def test_list_and_filter_collections(client: AsyncClient):
    """
    Test listing collections and filtering them by tags.
    """
    # Create two items with different tags
    await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "filter-1", "platform": "bilibili", "item_type": "video",
            "title": "Filter Test 1", "favorited_at": datetime.utcnow().isoformat()
        }
    )
    item2_resp = await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "filter-2", "platform": "bilibili", "item_type": "video",
            "title": "Filter Test 2", "favorited_at": datetime.utcnow().isoformat()
        }
    )
    item2_id = item2_resp.json()["id"]
    await client.post(f"/api/v1/collections/{item2_id}/tags", json={"tags": ["filter_tag"]})

    # List all
    response_list_all = await client.get("/api/v1/collections")
    assert response_list_all.status_code == 200
    assert response_list_all.json()["total"] >= 2 # Should have at least the two we just made

    # List with filter
    response_filtered = await client.get("/api/v1/collections?tags=filter_tag")
    assert response_filtered.status_code == 200
    filtered_data = response_filtered.json()
    assert filtered_data["total"] == 1
    assert filtered_data["items"][0]["title"] == "Filter Test 2"


async def test_delete_collection(client: AsyncClient):
    """
    Test deleting a collection.
    """
    # Create
    create_data = {
        "platform_item_id": "to-be-deleted", "platform": "xiaohongshu",
        "item_type": "note", "title": "To Be Deleted",
        "favorited_at": datetime.utcnow().isoformat()
    }
    response_create = await client.post("/api/v1/collections", json=create_data)
    collection_id = response_create.json()["id"]

    # Delete
    response_delete = await client.delete(f"/api/v1/collections/{collection_id}")
    assert response_delete.status_code == 204

    # Verify deletion
    response_read_deleted = await client.get(f"/api/v1/collections/{collection_id}")
    assert response_read_deleted.status_code == 404


async def test_inbox_list(client: AsyncClient):
    """Inbox should list only pending items by default."""
    # Create two items
    await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "inbox-1", "platform": "bilibili", "item_type": "video",
            "title": "Inbox 1", "favorited_at": datetime.utcnow().isoformat()
        }
    )
    await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "inbox-2", "platform": "bilibili", "item_type": "video",
            "title": "Inbox 2", "favorited_at": datetime.utcnow().isoformat()
        }
    )

    resp = await client.get("/api/v1/collections/inbox")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2

async def test_tag_filter_and_multi_tags(client: AsyncClient):
    """Support filtering by single tag and multiple tags (AND semantics)."""
    # Seed three items
    r1 = await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "mt-1", "platform": "bilibili", "item_type": "video",
            "title": "MT 1", "favorited_at": datetime.utcnow().isoformat()
        }
    )
    id1 = r1.json()["id"]
    r2 = await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "mt-2", "platform": "bilibili", "item_type": "video",
            "title": "MT 2", "favorited_at": datetime.utcnow().isoformat()
        }
    )
    id2 = r2.json()["id"]
    r3 = await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "mt-3", "platform": "bilibili", "item_type": "video",
            "title": "MT 3", "favorited_at": datetime.utcnow().isoformat()
        }
    )
    id3 = r3.json()["id"]

    # Add tags: id1 -> a; id2 -> b; id3 -> a,b
    await client.post(f"/api/v1/collections/{id1}/tags", json={"tags": ["a"]})
    await client.post(f"/api/v1/collections/{id2}/tags", json={"tags": ["b"]})
    await client.post(f"/api/v1/collections/{id3}/tags", json={"tags": ["a", "b"]})

    # Filter by single tag 'a'
    resp_a = await client.get("/api/v1/collections?tags=a")
    assert resp_a.status_code == 200
    items_a = resp_a.json()["items"]
    assert any(it["id"] == id1 for it in items_a)
    assert any(it["id"] == id3 for it in items_a)

    # Filter by two tags 'a,b' (AND semantics: item must have both)
    resp_ab = await client.get("/api/v1/collections?tags=a,b")
    assert resp_ab.status_code == 200
    items_ab = resp_ab.json()["items"]
    assert all("a" in [t["name"] for t in it.get("tags", [])] for it in items_ab)
    assert all("b" in [t["name"] for t in it.get("tags", [])] for it in items_ab)
    assert any(it["id"] == id3 for it in items_ab)
