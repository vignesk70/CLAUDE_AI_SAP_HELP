"""Orchestrates the ask flow: triage with Claude, retrieve from Mongo, answer.

    question
      -> ClaudeService.triage            -> HelpTriage
         needed_for_help_input == False  -> return triage.direct_answer
         needed_for_help_input == True   -> HelpRepository.search_many
                                         -> ClaudeService.answer_from_documents
"""

from __future__ import annotations

from typing import Any, Sequence

from app.models.chat import AskRequest, AskResponse, DocumentRef
from app.repositories.help_repository import HelpRepository
from app.services.claude_service import ClaudeService, claude_service

NO_MATCH_TEMPLATE = (
    "I could not find anything in the indexed SAP Help Portal content for this "
    "question (searched: {queries}).\n\n"
    "The local `help` collection only covers the topics that were seeded. To pull "
    "these in, run:\n\n"
    "```bash\n{seed_command}\n```"
)


class HelpAssistant:
    """Two-pass RAG over the `help` collection."""

    def __init__(
        self,
        repository: HelpRepository | None = None,
        claude: ClaudeService | None = None,
    ) -> None:
        self.repository = repository or HelpRepository()
        self.claude = claude or claude_service

    async def ask(self, request: AskRequest) -> AskResponse:
        """Answer a question, consulting the help collection only when needed."""
        triage = await self.claude.triage(request.question, request.history)

        if not triage.needed_for_help_input:
            return AskResponse(
                question=request.question,
                needed_for_help_input=False,
                reasoning=triage.reasoning,
                search_queries=[],
                answer=triage.direct_answer,
                confidence="high",
                model=self.claude.model,
            )

        queries = triage.search_queries or [request.question]
        documents = await self._retrieve(queries, triage.products, request.max_documents)

        if not documents:
            return AskResponse(
                question=request.question,
                needed_for_help_input=True,
                reasoning=triage.reasoning,
                search_queries=queries,
                answer=NO_MATCH_TEMPLATE.format(
                    queries=", ".join(repr(q) for q in queries),
                    seed_command=_seed_command(queries),
                ),
                confidence="low",
                model=self.claude.model,
            )

        grounded = await self.claude.answer_from_documents(
            request.question, documents, request.history
        )
        return AskResponse(
            question=request.question,
            needed_for_help_input=True,
            reasoning=triage.reasoning,
            search_queries=queries,
            answer=grounded.answer,
            citations=grounded.citations,
            confidence=grounded.confidence,
            followup_questions=grounded.followup_questions,
            retrieved_documents=[to_document_ref(doc) for doc in documents],
            model=self.claude.model,
        )

    async def _retrieve(
        self, queries: Sequence[str], products: Sequence[str], limit: int
    ) -> list[dict[str, Any]]:
        """Retrieve across every query, using Claude's products only as a boost.

        Claude names products freely, so treating them as a hard filter throws
        away good hits and keeps bad ones from whichever product it guessed.
        """
        return await self.repository.search_many(
            queries, boost_products=products, limit=limit
        )


def to_document_ref(doc: dict[str, Any]) -> DocumentRef:
    """Project a stored document onto the reference returned to the caller."""
    return DocumentRef(
        id=doc["_id"],
        loio=doc.get("loio", ""),
        title=doc.get("title", ""),
        url=doc.get("url", ""),
        product=doc.get("product", ""),
        score=doc.get("score"),
        rank_score=doc.get("rank_score"),
        matched_query=doc.get("matched_query", ""),
    )


def _seed_command(queries: Sequence[str]) -> str:
    args = " ".join(f'--query "{q}"' for q in queries)
    return f"python -m scripts.seed_help --refresh {args}".strip()

