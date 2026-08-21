"""Schema for documents stored in the `help` collection."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class HelpDocument(BaseModel):
    """A single SAP Help Portal topic.

    `id` is derived from the SAP `loio` (logical object id) plus the language so
    that re-seeding the same topic upserts instead of duplicating.
    """

    id: str = Field(..., alias="_id", description="<loio>:<language>")
    loio: str = Field(..., description="SAP logical object id")
    title: str
    description: str = ""
    snippet: str = Field(default="", description="Plain-text excerpt of the topic")
    url: str = Field(..., description="Absolute help.sap.com URL")
    product: str = ""
    product_id: str = ""
    version: str = ""
    version_id: str = ""
    deliverable_title: str = ""
    document_type: str = ""
    mime_type: str = ""
    language: str = "en-US"
    state: str = ""
    published_at: str = Field(default="", description="Publication date as reported by SAP (YYYY-MM-DD)")
    search_queries: list[str] = Field(
        default_factory=list, description="Seed queries that surfaced this topic"
    )
    source: str = "help.sap.com"
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}

    @staticmethod
    def make_id(loio: str, language: str) -> str:
        return f"{loio}:{language}"
