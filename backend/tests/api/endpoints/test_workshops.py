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

async def _ensure_workshop(client: AsyncClient):
    # Create a workshop if not already present
    resp_list = await client.get("/api/v1/workshops/manage")
    assert resp_list.status_code == 200
    existing = [w for w in resp_list.json() if w["workshop_id"] == "summary-01"]
    if not existing:
        payload = {
            "workshop_id": "summary-01",
            "name": "精华摘要",
            "description": "",
            "default_prompt": "请对以下内容进行精简摘要，保留要点与行动项。\n\n{source}",
            "default_model": None,
            "executor_type": "llm_chat",
            "executor_config": None,
        }
        resp_create = await client.post("/api/v1/workshops/manage", json=payload)
        assert resp_create.status_code == 200

async def test_workshop_crud_and_executor_config_roundtrip(client: AsyncClient):
    # Create
    payload = {
        "workshop_id": "custom-01",
        "name": "自定义",
        "description": "desc",
        "default_prompt": "hello {source}",
        "default_model": "m1",
        "executor_type": "llm_chat",
        "executor_config": {"temperature": 0.5},
    }
    resp_create = await client.post("/api/v1/workshops/manage", json=payload)
    assert resp_create.status_code == 200
    created = resp_create.json()
    assert created["executor_config"] == {"temperature": 0.5}

    # List and verify presence and parsed config
    resp_list = await client.get("/api/v1/workshops/manage")
    assert resp_list.status_code == 200
    items = resp_list.json()
    found = next((w for w in items if w["workshop_id"] == "custom-01"), None)
    assert found is not None
    assert found["executor_config"] == {"temperature": 0.5}

    # Update
    resp_update = await client.put(
        "/api/v1/workshops/manage/custom-01",
        json={"name": "改名", "executor_config": {"temperature": 0.7}},
    )
    assert resp_update.status_code == 200
    updated = resp_update.json()
    assert updated["name"] == "改名"
    assert updated["executor_config"] == {"temperature": 0.7}

    # Delete
    resp_delete = await client.delete("/api/v1/workshops/manage/custom-01")
    assert resp_delete.status_code == 200
    # Ensure gone
    resp_list2 = await client.get("/api/v1/workshops/manage")
    items2 = resp_list2.json()
    assert all(w["workshop_id"] != "custom-01" for w in items2)

async def test_list_available_workshops_basic(client: AsyncClient):
    # Ensure one workshop exists
    await _ensure_workshop(client)
    resp = await client.get("/api/v1/workshops")
    assert resp.status_code == 200
    data = resp.json()
    # Should return a list of {id, name}
    assert isinstance(data, list)
    assert any(w["id"] == "summary-01" for w in data)

@patch("app.services.workshop_service.run_workshop_task", new_callable=AsyncMock)
async def test_execute_workshop_and_get_status(mock_run_task, client: AsyncClient):
    """Test executing a workshop and then polling the task status."""
    await _ensure_workshop(client)
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

@pytest.mark.skip(reason="not implemented")
async def test_websocket_communication(client: AsyncClient, db_session: AsyncSession):
    """
    Integration-style check without real WebSocket: start a task and poll status
    until it reports success, then validate the result content.
    """
    await _ensure_workshop(client)
    item_id = await create_test_item(client)
    
    # Make the task runner deterministic and fast by patching sleeps and executor
    with \
        patch("app.services.workshop_service.asyncio.sleep", new=AsyncMock(return_value=None)), \
        patch("app.services.executors.execute_llm_chat", new=AsyncMock(return_value="summary generated content")):
    
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


@patch("app.api.endpoints.workshops.toggle_workshop_listening", new_callable=AsyncMock)
async def test_toggle_listening_success(mock_toggle, client: AsyncClient):
    await _ensure_workshop(client)
    mock_toggle.return_value = {"ok": True, "enabled": True}
    resp = await client.post("/api/v1/workshops/manage/summary-01/toggle-listening", json={"enabled": True, "workshop_name": "精华摘要"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True


@patch("app.api.endpoints.workshops.toggle_workshop_listening", new_callable=AsyncMock)
async def test_toggle_listening_not_found(mock_toggle, client: AsyncClient):
    mock_toggle.return_value = {"ok": False}
    resp = await client.post("/api/v1/workshops/manage/not-exist/toggle-listening", json={"enabled": True, "workshop_name": "不存在"})
    assert resp.status_code == 404


async def test_update_listening_binding_roundtrip(client: AsyncClient):
    await _ensure_workshop(client)

    # Bind to a collection_id
    resp_bind = await client.put(
        "/api/v1/workshops/manage/summary-01/binding", json={"collection_id": 123}
    )
    assert resp_bind.status_code == 200
    assert resp_bind.json()["binding_collection_id"] == 123

    # Verify persisted executor_config
    ws_resp = await client.get("/api/v1/workshops/manage/summary-01")
    assert ws_resp.status_code == 200
    cfg = ws_resp.json().get("executor_config")
    assert isinstance(cfg, dict)
    assert cfg.get("binding_collection_id") == 123

    # Unbind (set to null)
    resp_unbind = await client.put(
        "/api/v1/workshops/manage/summary-01/binding", json={"collection_id": None}
    )
    assert resp_unbind.status_code == 200
    assert resp_unbind.json()["binding_collection_id"] is None

    # Verify removal from config (empty dict or missing key)
    ws_resp2 = await client.get("/api/v1/workshops/manage/summary-01")
    assert ws_resp2.status_code == 200
    cfg2 = ws_resp2.json().get("executor_config") or {}
    assert "binding_collection_id" not in cfg2 or cfg2.get("binding_collection_id") is None