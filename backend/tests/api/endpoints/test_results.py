import pytest
from httpx import AsyncClient
from datetime import datetime
from unittest.mock import patch, AsyncMock

from app.db.models import Result, FavoriteItem
from app.schemas.unified import ResultCreate
from app.crud import crud_favorites
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

async def create_test_item_and_result(
    client: AsyncClient, db: AsyncSession
) -> tuple[int, int]:
    """Helper function to create a favorite item and an initial result."""
    # Create an item
    item_resp = await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "result-item-1", "platform": "bilibili", "item_type": "video",
            "title": "Result Test", "favorited_at": datetime.utcnow().isoformat()
        }
    )
    item_id = item_resp.json()["id"]

    # Manually create a result for it using the db session fixture
    new_result = Result(workshop_id="summary-01", content="Initial content", favorite_item_id=item_id)
    db.add(new_result)
    await db.commit()
    await db.refresh(new_result)
    result_id = new_result.id
    
    return item_id, result_id

async def test_update_result(client: AsyncClient, db_session: AsyncSession):
    """Test updating the content of a result."""
    item_id, result_id = await create_test_item_and_result(client, db_session)
    
    update_data = {"content": "Updated content"}
    response = await client.put(f"/api/v1/results/{result_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["content"] == "Updated content"

async def test_delete_result(client: AsyncClient, db_session: AsyncSession):
    """Test deleting a result."""
    item_id, result_id = await create_test_item_and_result(client, db_session)

    response = await client.delete(f"/api/v1/results/{result_id}")
    assert response.status_code == 204

    # Verify it's gone
    item_resp = await client.get(f"/api/v1/collections/{item_id}")
    assert len(item_resp.json()["results"]) == 0


@patch("app.services.workshop_service.run_workshop_task", new_callable=AsyncMock)
async def test_regenerate_result(
    mock_run_task, client: AsyncClient, db_session: AsyncSession
):
    """Test regenerating a result, ensuring a background task is called."""
    item_id, result_id = await create_test_item_and_result(client, db_session)

    response = await client.post(f"/api/v1/results/{result_id}/regenerate")
    assert response.status_code == 202
    
    task_data = response.json()
    assert task_data["id"] is not None
    assert task_data["workshop_id"] == "summary-01"
    
    # Check that our background task runner was called correctly
    mock_run_task.assert_called_once()
    call_args = mock_run_task.call_args[1]
    assert call_args["task_id"] == task_data["id"]
    assert call_args["result_to_update_id"] == result_id
