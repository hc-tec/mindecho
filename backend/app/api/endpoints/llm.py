from fastapi import APIRouter, Depends
from pydantic import BaseModel
from client_sdk.rpc_client_async import EAIRPCClient

router = APIRouter()

class LLMRequest(BaseModel):
    prompt: str
    model: str = "gemini-2.5-flash-preview-05-20"

class LLMResponse(BaseModel):
    response: str

@router.post("/llm/call", response_model=LLMResponse)
async def call_llm(
    request: LLMRequest,
):
    """
    Proxy endpoint to call the LLM service securely from the backend.
    """
    client = EAIRPCClient(base_url="http://127.0.0.1:8008", api_key="testkey")
    response_text = ""
    try:
        await client.start()
        # This assumes your client_sdk has a method like `chat_with_yuanbao`
        # and it returns a dictionary with a 'text' key.
        # This may need adjustment based on the actual client_sdk implementation.
        result = await client.chat_with_yuanbao(
            prompt=request.prompt,
            model=request.model
        )
        response_text = result.get("text", "Error: No text in response")
    except Exception as e:
        response_text = f"Error calling LLM: {e}"
    finally:
        await client.stop()
        
    return {"response": response_text}
