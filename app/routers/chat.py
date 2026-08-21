from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.dependencies import get_help_repository
from app.models.chat import ChatMessage
from app.repositories.help_repository import HelpRepository
from app.services.claude_service import ClaudeServiceError, claude_service

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a conversation to Claude and receive a response.

    This is the raw pass-through. For answers grounded in the seeded SAP Help
    Portal content, use `POST /api/help/ask`.
    """
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    try:
        reply = await claude_service.chat(messages)
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # report the upstream cause
        raise HTTPException(status_code=500, detail=f"Claude API error: {exc}") from exc
    return ChatResponse(reply=reply)


@router.get("/health")
async def health_check(
    repository: Annotated[HelpRepository, Depends(get_help_repository)],
) -> dict[str, Any]:
    """Report API, database, and corpus status."""
    database: dict[str, Any] = {"status": "ok"}
    try:
        database["documents"] = await repository.count()
    except Exception as exc:  # health must report, not raise
        database = {"status": "error", "detail": f"{type(exc).__name__}: {exc}"}

    return {
        "status": "ok" if database["status"] == "ok" else "degraded",
        "model": settings.claude_model,
        "database": {**database, "name": settings.mongodb_database},
    }
