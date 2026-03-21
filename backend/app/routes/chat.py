"""Chat API endpoint — connects to the LLM chat handler."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.llm import handle_chat_message

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat_endpoint(body: ChatRequest, request: Request) -> dict:
    """Send a message to the AI assistant and receive a response with optional actions."""
    price_cache = request.app.state.price_cache
    return await handle_chat_message(body.message, price_cache)
