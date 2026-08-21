"""FastAPI dependency providers.

Async providers, built per request rather than at import time, so the Mongo
client is created on — and bound to — the running event loop.
"""

from __future__ import annotations

from app.repositories.help_repository import HelpRepository
from app.services.help_assistant import HelpAssistant


async def get_help_repository() -> HelpRepository:
    """Provide the help repository (the Mongo client underneath is shared)."""
    return HelpRepository()


async def get_help_assistant() -> HelpAssistant:
    """Provide the ask orchestrator."""
    return HelpAssistant(repository=HelpRepository())
