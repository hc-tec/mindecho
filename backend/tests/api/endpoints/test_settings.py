import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_get_and_update_settings(client: AsyncClient):
    """
    Test getting the default settings and then updating them.
    """
    # Get initial settings
    response_get = await client.get("/api/v1/settings")
    assert response_get.status_code == 200
    initial_settings = response_get.json()
    assert initial_settings["theme"] == "dark"

    # Update settings
    update_data = {
        "theme": "light",
        "notifications_enabled": False,
        "ai_model": "new-test-model",
        # also update category map to ensure it roundtrips via runtime_config
        "category_to_workshop": {"education": "summary-01"}
    }
    response_put = await client.put("/api/v1/settings", json=update_data)
    assert response_put.status_code == 200
    updated_settings = response_put.json()
    assert updated_settings["theme"] == "light"
    assert updated_settings["notifications_enabled"] is False

    # Get settings again to verify persistence and category map exposure
    response_get_again = await client.get("/api/v1/settings")
    assert response_get_again.status_code == 200
    final_settings = response_get_again.json()
    assert final_settings["theme"] == "light"
    assert final_settings["category_to_workshop"] == {"education": "summary-01"}
