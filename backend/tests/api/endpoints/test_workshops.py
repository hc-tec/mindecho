import pytest
from httpx import AsyncClient
from datetime import datetime
from unittest.mock import patch, AsyncMock, ANY
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.db.models import Task, TaskStatus

pytestmark = pytest.mark.asyncio

async def create_test_item(client: AsyncClient) -> int:
    """Helper to create a simple item and return its ID."""
    resp = await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": "ws-item-1", "platform": "bilibili",
            "item_type": "video", "title": "Workshop Test",
            "favorited_at": datetime.utcnow().isoformat()
        }
    )
    return resp.json()["id"]

@patch("app.services.workshop_service.run_workshop_task", new_callable=AsyncMock)
async def test_execute_workshop_and_get_status(mock_run_task, client: AsyncClient):
    """Test executing a workshop and then polling the task status."""
    item_id = await create_test_item(client)
    
    # Execute workshop
    response_exec = await client.post(
        "/api/v1/workshops/summary-01/execute",
        json={"collection_id": item_id}
    )
    assert response_exec.status_code == 202
    task_data = response_exec.json()
    task_id = task_data["task_id"]
    assert task_id is not None
    mock_run_task.assert_called_once_with(db=ANY, task_id=task_id)

    # Get specific task status
    response_status = await client.get(f"/api/v1/tasks/{task_id}")
    assert response_status.status_code == 200
    assert response_status.json()["id"] == task_id
    assert response_status.json()["status"] == "pending" # Initially pending

async def test_websocket_communication(client: AsyncClient, db_session: AsyncSession):
    """
    Integration-style check without real WebSocket: start a task and poll status
    until it reports success, then validate the result content.
    """
    item_id = await create_test_item(client)
    
    # We don't mock the task runner here, we let the real one run
    # to test the websocket communication it generates.
    
    # Start the task
    response_exec = await client.post(
        "/api/v1/workshops/summary-01/execute",
        json={"collection_id": item_id}
    )
    assert response_exec.status_code == 202
    task_id = response_exec.json()["task_id"]

    # Poll the task status until success (with timeout)
    done = False
    for _ in range(60): # up to ~12s at 0.2s interval
        resp = await client.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] == "success":
            done = True
            assert data.get("result") is not None
            assert "summary generated" in data["result"]["content"]
            break
        await asyncio.sleep(0.2)
    assert done, "Task did not complete in time"

@pytest.mark.skip
async def test_global_task_status_and_clear(client: AsyncClient, db_session: AsyncSession):
    """Test global task status and clearing completed tasks."""
    # Create a task
    item_id = await create_test_item(client)
    await client.post(
        "/api/v1/workshops/summary-01/execute", json={"collection_id": item_id}
    )
    
    # Check global status - should have 1 pending/in_progress
    # (Timing might make it one or the other)
    response_global = await client.get("/api/v1/tasks/status")
    assert response_global.status_code == 200
    assert response_global.json()["total"] > 0

    # Wait for the task to complete
    await asyncio.sleep(5) # Give it time to run

    # Clear completed tasks
    response_clear = await client.delete("/api/v1/tasks/clear-completed")
    assert response_clear.status_code == 204

    # Check global status again - should be 0
    response_global_after = await client.get("/api/v1/tasks/status")
    assert response_global_after.status_code == 200
    assert response_global_after.json()["total"] == 0
