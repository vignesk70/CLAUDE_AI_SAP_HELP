from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.claude_service import claude_service

router = APIRouter(prefix="/api", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a conversation to Claude and receive a response."""
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    try:
        reply = await claude_service.chat(messages)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Claude API error: {exc}") from exc
    return ChatResponse(reply=reply)


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Simple health-check endpoint."""
    return {"status": "ok"}
