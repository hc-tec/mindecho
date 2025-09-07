import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_rpc_client_llm(monkeypatch):
    """Fixture to mock the EAIRPCClient for LLM calls."""
    mock_client = MagicMock()
    mock_client.start = AsyncMock()
    mock_client.stop = AsyncMock()
    
    mock_client.chat_with_yuanbao = AsyncMock(return_value={
        "text": "This is a mock LLM response."
    })

    monkeypatch.setattr("app.api.endpoints.llm.EAIRPCClient", lambda *args, **kwargs: mock_client)
    return mock_client

async def test_call_llm(client: AsyncClient, mock_rpc_client_llm):
    """Test the LLM proxy endpoint."""
    request_data = {
        "prompt": "Hello, world!",
        "model": "test-model"
    }
    
    response = await client.post("/api/v1/llm/call", json=request_data)
    
    assert response.status_code == 200
    assert response.json()["response"] == "This is a mock LLM response."
    
    # Verify the underlying RPC client was called correctly
    mock_rpc_client_llm.chat_with_yuanbao.assert_called_once_with(
        prompt="Hello, world!",
        model="test-model"
    )
