"""Request/response models for the ask + chat endpoints, and the schemas Claude
is constrained to when it answers.

Two Claude passes are involved:

1. `HelpTriage`   — does this question need SAP Help Portal content?
2. `GroundedAnswer` — the final answer, written only from the documents we fed in.

Both are produced with `client.messages.parse(output_format=...)`, so the models
below double as the JSON schema Claude must satisfy. Keep them flat and keep
every field required-with-a-default: nested optionals make the generated schema
harder for the model to satisfy.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]


class ChatMessage(BaseModel):
    """One turn of conversation."""

    role: Literal["user", "assistant"]
    content: str


class HelpTriage(BaseModel):
    """Claude's first-pass decision: is help.sap.com content needed?"""

    needed_for_help_input: bool = Field(
        ...,
        description=(
            "True when answering requires SAP Help Portal documentation. False for "
            "greetings, meta questions, or things you already know exactly."
        ),
    )
    reasoning: str = Field(..., description="One or two sentences explaining the decision.")
    search_queries: list[str] = Field(
        default_factory=list,
        description=(
            "Full-text queries to run against the help collection. 1-4 short, "
            "keyword-style queries. Empty when needed_for_help_input is false."
        ),
    )
    products: list[str] = Field(
        default_factory=list,
        description=(
            "Optional SAP product filter, e.g. 'ABAP platform', 'SAP S/4HANA'. "
            "Leave empty to search every product."
        ),
    )
    direct_answer: str = Field(
        default="",
        description=(
            "The complete answer, filled in only when needed_for_help_input is false. "
            "Empty otherwise."
        ),
    )


class HelpCitation(BaseModel):
    """A help topic Claude actually leaned on."""

    loio: str = Field(..., description="loio of the cited topic")
    title: str
    url: str


class GroundedAnswer(BaseModel):
    """Claude's second-pass answer, grounded in retrieved help documents."""

    answer: str = Field(..., description="The answer, in markdown.")
    citations: list[HelpCitation] = Field(
        default_factory=list, description="Only documents that informed the answer."
    )
    confidence: Confidence = Field(
        ..., description="How well the supplied documents cover the question."
    )
    followup_questions: list[str] = Field(
        default_factory=list, description="Up to three useful follow-up questions."
    )


class DocumentRef(BaseModel):
    """A retrieved document as reported back to the caller."""

    id: str
    loio: str
    title: str
    url: str
    product: str = ""
    score: float | None = Field(default=None, description="Raw MongoDB text score")
    rank_score: float | None = Field(
        default=None,
        description="Score after the product boost — this is what ordering uses",
    )
    matched_query: str = ""


class AskRequest(BaseModel):
    """A question from the user, plus optional prior turns."""

    question: str = Field(..., min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(
        default_factory=list, description="Prior turns, oldest first."
    )
    max_documents: int = Field(default=6, ge=1, le=20)


class AskResponse(BaseModel):
    """The full result of one ask, including how it was routed."""

    question: str
    needed_for_help_input: bool
    reasoning: str
    search_queries: list[str] = Field(default_factory=list)
    answer: str
    citations: list[HelpCitation] = Field(default_factory=list)
    confidence: Confidence = "medium"
    followup_questions: list[str] = Field(default_factory=list)
    retrieved_documents: list[DocumentRef] = Field(default_factory=list)
    model: str
