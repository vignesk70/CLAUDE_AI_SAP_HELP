"""Claude API integration.

Three call shapes:

* `chat`                  — plain conversational reply (the original `/api/chat`).
* `triage`                — structured `HelpTriage`, decides whether SAP Help
                            Portal content is needed and what to search for.
* `answer_from_documents` — structured `GroundedAnswer` written only from the
                            help documents we retrieved.

The two structured calls use `client.messages.parse(output_format=...)`, so the
Pydantic models in `app.models.chat` *are* the schema Claude must satisfy — no
prompt-level "reply with JSON" instructions and no parsing on our side.
"""

from __future__ import annotations

import json
from typing import Any, Sequence

import anthropic

from app.config import settings
from app.models.chat import ChatMessage, GroundedAnswer, HelpTriage


class ClaudeServiceError(RuntimeError):
    """Raised when Claude cannot produce a usable response."""


class ClaudeService:
    """Wraps the Anthropic Claude API for SAP support conversations."""

    SYSTEM_PROMPT = (
        "You are an expert SAP support assistant. "
        "You help developers and administrators with SAP configuration, "
        "ABAP development, troubleshooting, and best practices. "
        "Provide clear, actionable answers with references to relevant "
        "SAP transactions, tables, or OSS notes when applicable."
    )

    TRIAGE_PROMPT = (
        "You are the routing step of an SAP support assistant.\n\n"
        "Decide whether answering the user's question requires official SAP Help "
        "Portal documentation that has been indexed locally.\n\n"
        "Set needed_for_help_input to true when the question is about SAP products, "
        "transactions, configuration, ABAP, BTP, Fiori, HANA, or anything where "
        "citing SAP documentation matters. In that case leave direct_answer empty "
        "and provide 1-4 short keyword-style search_queries — the local index is a "
        "MongoDB full-text index over topic titles, descriptions and snippets, so "
        "prefer product and feature keywords ('transport request STMS', 'CDS view "
        "entity') over full sentences.\n\n"
        "Set needed_for_help_input to false only for greetings, small talk, "
        "questions about this assistant itself, or non-SAP questions. Then answer "
        "the user directly in direct_answer and leave search_queries empty."
    )

    ANSWER_PROMPT = (
        "You are an expert SAP support assistant answering from SAP Help Portal "
        "documentation that has been retrieved for you.\n\n"
        "Ground your answer in the supplied documents. Cite the documents you "
        "actually used in citations, copying their loio, title and url verbatim; "
        "never invent a citation or a URL. If the documents only partially cover "
        "the question, answer what they support, say plainly what is missing, and "
        "set confidence to medium or low. If they do not cover it at all, say so "
        "and set confidence to low — do not fall back to unsourced recall without "
        "labelling it as such.\n\n"
        "Write the answer as markdown. Mention concrete SAP transactions, tables "
        "and report names where the documents provide them."
    )

    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.max_tokens = settings.max_tokens

    # ------------------------------------------------------------------ chat

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a conversation to Claude and return the assistant's reply.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."} dicts.

        Returns:
            The text content of Claude's response.
        """
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.SYSTEM_PROMPT,
            messages=messages,
        )
        _reject_refusal(response)
        return "".join(block.text for block in response.content if block.type == "text")

    # ------------------------------------------------------- structured calls

    async def triage(self, question: str, history: Sequence[ChatMessage] = ()) -> HelpTriage:
        """Ask Claude whether the question needs help-portal input, and what to search."""
        response = await self.client.messages.parse(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.TRIAGE_PROMPT,
            messages=[*_as_messages(history), {"role": "user", "content": question}],
            output_format=HelpTriage,
        )
        return _parsed(response, HelpTriage)

    async def answer_from_documents(
        self,
        question: str,
        documents: Sequence[dict[str, Any]],
        history: Sequence[ChatMessage] = (),
    ) -> GroundedAnswer:
        """Answer the question using only the supplied help documents."""
        context = render_documents(documents)
        user_content = (
            f"<help_documents>\n{context}\n</help_documents>\n\n"
            f"Question: {question}"
        )
        response = await self.client.messages.parse(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.ANSWER_PROMPT,
            messages=[*_as_messages(history), {"role": "user", "content": user_content}],
            output_format=GroundedAnswer,
        )
        return _parsed(response, GroundedAnswer)


def render_documents(documents: Sequence[dict[str, Any]]) -> str:
    """Render retrieved documents as the JSON context block Claude reads.

    Only the fields Claude needs are included: extra fields (scores, seed
    metadata) waste tokens and invite the model to cite them.
    """
    if not documents:
        return "[]"
    trimmed = [
        {
            "loio": doc.get("loio", ""),
            "title": doc.get("title", ""),
            "url": doc.get("url", ""),
            "product": doc.get("product", ""),
            "version": doc.get("version", ""),
            "deliverable": doc.get("deliverable_title", ""),
            "description": doc.get("description", ""),
            "snippet": doc.get("snippet", ""),
        }
        for doc in documents
    ]
    return json.dumps(trimmed, indent=2, ensure_ascii=False)


def _as_messages(history: Sequence[ChatMessage]) -> list[dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in history]


def _reject_refusal(response: Any) -> None:
    """Turn a safety refusal into an explicit error instead of empty content."""
    if getattr(response, "stop_reason", None) == "refusal":
        details = getattr(response, "stop_details", None)
        category = getattr(details, "category", None) or "unspecified"
        raise ClaudeServiceError(f"Claude declined to answer (category: {category})")


def _parsed(response: Any, expected: type) -> Any:
    """Return the validated structured output, or raise with the reason it is missing."""
    _reject_refusal(response)
    parsed = getattr(response, "parsed_output", None)
    if parsed is None:
        raise ClaudeServiceError(
            f"Claude returned no {expected.__name__} "
            f"(stop_reason={getattr(response, 'stop_reason', 'unknown')})"
        )
    return parsed


claude_service = ClaudeService()
