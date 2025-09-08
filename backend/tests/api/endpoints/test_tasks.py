import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.models import Task as TaskModel, TaskStatus, Result as ResultModel

pytestmark = pytest.mark.asyncio

async def _create_collection(client: AsyncClient, platform_item_id: str = "task-item-1") -> int:
    resp = await client.post(
        "/api/v1/collections",
        json={
            "platform_item_id": platform_item_id,
            "platform": "bilibili",
            "item_type": "video",
            "title": f"Item {platform_item_id}",
            "favorited_at": datetime.utcnow().isoformat(),
        },
    )
    return resp.json()["id"]

async def test_read_task_status_with_eager_loaded_result(client: AsyncClient, db_session: AsyncSession):
    """Task detail should include eager-loaded result without lazy loads."""
    item_id = await _create_collection(client, platform_item_id="task-item-eager")

    # Create a SUCCESS task
    task = TaskModel(status=TaskStatus.SUCCESS, workshop_id="summary-01", favorite_item_id=item_id)
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    # Attach a result to this task
    result = ResultModel(workshop_id="summary-01", content="ok", favorite_item_id=item_id, task_id=task.id)
    db_session.add(result)
    await db_session.commit()

    resp = await client.get(f"/api/v1/tasks/{task.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == task.id
    assert data["result"] is not None
    assert data["result"]["content"] == "ok"

async def test_global_status_and_clear_completed(client: AsyncClient, db_session: AsyncSession):
    """Global status should reflect counts; clear-completed should remove SUCCESS/FAILURE tasks."""
    # Seed tasks of different statuses
    t1 = TaskModel(status=TaskStatus.PENDING, workshop_id="w1")
    t2 = TaskModel(status=TaskStatus.IN_PROGRESS, workshop_id="w1")
    t3 = TaskModel(status=TaskStatus.SUCCESS, workshop_id="w1")
    t4 = TaskModel(status=TaskStatus.FAILURE, workshop_id="w1")
    db_session.add_all([t1, t2, t3, t4])
    await db_session.commit()

    resp1 = await client.get("/api/v1/tasks/status")
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert body1["pending"] >= 1
    assert body1["in_progress"] >= 1
    assert body1["total"] == body1["pending"] + body1["in_progress"]

    # Clear completed
    resp_clear = await client.delete("/api/v1/tasks/clear-completed")
    assert resp_clear.status_code == 204

    resp2 = await client.get("/api/v1/tasks/status")
    assert resp2.status_code == 200
    body2 = resp2.json()
    # Completed removed; totals recomputed
    assert body2["total"] == body2["pending"] + body2["in_progress"]

@patch("app.services.workshop_service.run_workshop_task", new_callable=AsyncMock)
async def test_regenerate_result_creates_task_and_readable(mock_run_task, client: AsyncClient, db_session: AsyncSession):
    """Regenerating a result should create a task; we can then read the task by id."""
    item_id = await _create_collection(client, platform_item_id="task-item-recreate")

    # Seed a result for the item
    res = ResultModel(workshop_id="summary-01", content="seed", favorite_item_id=item_id)
    db_session.add(res)
    await db_session.commit()
    await db_session.refresh(res)

    # Call regenerate
    resp = await client.post(f"/api/v1/results/{res.id}/regenerate")
    assert resp.status_code == 202
    task = resp.json()
    assert task["id"] is not None

    # Read the task
    task_resp = await client.get(f"/api/v1/tasks/{task['id']}")
    assert task_resp.status_code == 200

async def test_read_task_status_404_for_nonexistent(client: AsyncClient):
    resp = await client.get("/api/v1/tasks/999999")
    assert resp.status_code == 404