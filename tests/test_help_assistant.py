"""Unit tests for the ask flow. No network, no database — Claude and the
repository are both stubbed so only the routing logic is under test."""

import unittest

from app.models.chat import AskRequest, ChatMessage, GroundedAnswer, HelpCitation, HelpTriage
from app.services.claude_service import render_documents
from app.services.help_assistant import HelpAssistant, to_document_ref

DOCUMENT = {
    "_id": "aaa1:en-US",
    "loio": "aaa1",
    "title": "Creating a transport request",
    "url": "https://help.sap.com/docs/aaa1.html",
    "product": "SAP S/4HANA",
    "description": "",
    "snippet": "Use STMS to release transports.",
    "deliverable_title": "Change and Transport System",
    "version": "2025",
    "score": 4.5,
    "rank_score": 7.2,
    "matched_query": "transport request",
    "seeded_at": "ignored",
}


class FakeClaude:
    """Records the calls made to it and replays canned structured output."""

    model = "claude-test"

    def __init__(self, triage: HelpTriage, answer: GroundedAnswer | None = None) -> None:
        self._triage = triage
        self._answer = answer
        self.triage_calls: list[tuple[str, tuple]] = []
        self.answer_calls: list[tuple[str, list]] = []

    async def triage(self, question, history=()):
        self.triage_calls.append((question, tuple(history)))
        return self._triage

    async def answer_from_documents(self, question, documents, history=()):
        self.answer_calls.append((question, list(documents)))
        return self._answer


class FakeRepository:
    """Returns a fixed result set and records the arguments it was given."""

    def __init__(self, results) -> None:
        self._results = results
        self.calls: list[dict] = []

    async def search_many(
        self, queries, boost_products=None, limit=6, per_query_limit=None
    ):
        self.calls.append(
            {
                "queries": list(queries),
                "boost_products": list(boost_products or []),
                "limit": limit,
            }
        )
        return self._results


GROUNDED = GroundedAnswer(
    answer="Use SE09 then release via STMS.",
    citations=[HelpCitation(loio="aaa1", title=DOCUMENT["title"], url=DOCUMENT["url"])],
    confidence="high",
    followup_questions=["How do I check the import queue?"],
)


class AskFlowTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_help_needed_returns_direct_answer_without_touching_db(self):
        claude = FakeClaude(
            HelpTriage(
                needed_for_help_input=False,
                reasoning="Greeting.",
                direct_answer="Hello! Ask me about SAP.",
            )
        )
        repository = FakeRepository([DOCUMENT])
        assistant = HelpAssistant(repository=repository, claude=claude)

        response = await assistant.ask(AskRequest(question="hi"))

        self.assertFalse(response.needed_for_help_input)
        self.assertEqual(response.answer, "Hello! Ask me about SAP.")
        self.assertEqual(response.confidence, "high")
        self.assertEqual(response.retrieved_documents, [])
        self.assertEqual(repository.calls, [])
        self.assertEqual(claude.answer_calls, [])

    async def test_help_needed_retrieves_then_answers(self):
        claude = FakeClaude(
            HelpTriage(
                needed_for_help_input=True,
                reasoning="Needs SAP docs.",
                search_queries=["transport request"],
                products=["SAP S/4HANA"],
            ),
            GROUNDED,
        )
        repository = FakeRepository([DOCUMENT])
        assistant = HelpAssistant(repository=repository, claude=claude)

        response = await assistant.ask(
            AskRequest(question="How do I move a change to QA?", max_documents=3)
        )

        self.assertTrue(response.needed_for_help_input)
        self.assertEqual(response.search_queries, ["transport request"])
        self.assertEqual(response.answer, GROUNDED.answer)
        self.assertEqual(response.citations, GROUNDED.citations)
        self.assertEqual(response.confidence, "high")
        self.assertEqual(response.model, "claude-test")
        self.assertEqual(repository.calls[0]["limit"], 3)
        self.assertEqual(repository.calls[0]["boost_products"], ["SAP S/4HANA"])
        self.assertEqual(len(claude.answer_calls), 1)
        self.assertEqual([d.loio for d in response.retrieved_documents], ["aaa1"])

    async def test_falls_back_to_question_when_claude_gives_no_queries(self):
        claude = FakeClaude(
            HelpTriage(needed_for_help_input=True, reasoning="Needs docs."), GROUNDED
        )
        repository = FakeRepository([DOCUMENT])
        assistant = HelpAssistant(repository=repository, claude=claude)

        response = await assistant.ask(AskRequest(question="IDoc stuck in status 51"))

        self.assertEqual(repository.calls[0]["queries"], ["IDoc stuck in status 51"])
        self.assertEqual(response.search_queries, ["IDoc stuck in status 51"])

    async def test_claude_products_are_passed_as_a_boost_not_a_filter(self):
        # A wrong product guess must not narrow retrieval — one search, boosted.
        claude = FakeClaude(
            HelpTriage(
                needed_for_help_input=True,
                reasoning="Needs docs.",
                search_queries=["transport request"],
                products=["Nonexistent Product"],
            ),
            GROUNDED,
        )
        repository = FakeRepository([DOCUMENT])
        assistant = HelpAssistant(repository=repository, claude=claude)

        response = await assistant.ask(AskRequest(question="transports?"))

        self.assertEqual(len(repository.calls), 1)
        self.assertEqual(repository.calls[0]["boost_products"], ["Nonexistent Product"])
        self.assertEqual(response.answer, GROUNDED.answer)

    async def test_no_documents_short_circuits_before_second_claude_call(self):
        claude = FakeClaude(
            HelpTriage(
                needed_for_help_input=True,
                reasoning="Needs docs.",
                search_queries=["obscure topic"],
            )
        )
        repository = FakeRepository([])
        assistant = HelpAssistant(repository=repository, claude=claude)

        response = await assistant.ask(AskRequest(question="something unseeded"))

        self.assertEqual(claude.answer_calls, [])
        self.assertEqual(response.confidence, "low")
        self.assertIn("scripts.seed_help --refresh", response.answer)
        self.assertIn("obscure topic", response.answer)

    async def test_history_is_forwarded_to_both_passes(self):
        history = [ChatMessage(role="user", content="earlier"), ChatMessage(role="assistant", content="ok")]
        claude = FakeClaude(
            HelpTriage(
                needed_for_help_input=True, reasoning="Needs docs.", search_queries=["transport"]
            ),
            GROUNDED,
        )
        assistant = HelpAssistant(repository=FakeRepository([DOCUMENT]), claude=claude)

        await assistant.ask(AskRequest(question="and now?", history=history))

        self.assertEqual(claude.triage_calls[0][1], tuple(history))


class DocumentRenderingTest(unittest.TestCase):
    def test_document_ref_projection(self):
        ref = to_document_ref(DOCUMENT)
        self.assertEqual(ref.id, "aaa1:en-US")
        self.assertEqual(ref.score, 4.5)
        self.assertEqual(ref.rank_score, 7.2)
        self.assertEqual(ref.matched_query, "transport request")

    def test_render_documents_drops_internal_fields(self):
        rendered = render_documents([DOCUMENT])
        self.assertIn("Creating a transport request", rendered)
        self.assertNotIn("seeded_at", rendered)
        self.assertNotIn("matched_query", rendered)
        self.assertNotIn("rank_score", rendered)

    def test_render_documents_handles_empty(self):
        self.assertEqual(render_documents([]), "[]")


if __name__ == "__main__":
    unittest.main()
