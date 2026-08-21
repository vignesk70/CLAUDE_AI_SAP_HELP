"""Endpoint tests. Claude and MongoDB are replaced with dependency overrides,
so these run offline. TestClient is used without a context manager so the app
lifespan (which touches Mongo) does not run."""

import unittest

from fastapi.testclient import TestClient

from app.dependencies import get_help_assistant, get_help_repository
from app.main import app
from app.models.chat import AskResponse, HelpCitation
from app.services.claude_service import ClaudeServiceError

DOCUMENT = {
    "_id": "aaa1:en-US",
    "loio": "aaa1",
    "title": "Creating a transport request",
    "url": "https://help.sap.com/docs/aaa1.html",
    "product": "SAP S/4HANA",
    "product_id": "SAP_S4HANA",
    "document_type": "Topic",
    "snippet": "Use STMS to release transports.",
    "score": 4.5,
}

ASK_RESPONSE = AskResponse(
    question="How do I move a change to QA?",
    needed_for_help_input=True,
    reasoning="Needs SAP docs.",
    search_queries=["transport request"],
    answer="Use SE09, then release via STMS.",
    citations=[HelpCitation(loio="aaa1", title=DOCUMENT["title"], url=DOCUMENT["url"])],
    confidence="high",
    model="claude-test",
)


class StubAssistant:
    def __init__(self, response=ASK_RESPONSE, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.requests = []

    async def ask(self, request):
        self.requests.append(request)
        if self._error:
            raise self._error
        return self._response


class StubRepository:
    def __init__(self, documents=(DOCUMENT,), error: Exception | None = None) -> None:
        self._documents = list(documents)
        self._error = error

    async def count(self, product_id=None, document_type=None):
        if self._error:
            raise self._error
        return len(self._documents)

    async def get(self, document_id):
        return next((d for d in self._documents if d["_id"] == document_id), None)

    async def list(self, product_id=None, document_type=None, skip=0, limit=20):
        return self._documents[skip : skip + limit]

    async def search(self, query, products=None, document_types=None, limit=6):
        return self._documents[:limit]

    async def products(self, limit=50):
        return [{"product": "SAP S/4HANA", "product_id": "SAP_S4HANA", "count": 1}]

    async def document_types(self, limit=50):
        return [{"document_type": "Topic", "count": 1}]


class ApiTestCase(unittest.TestCase):
    def override(self, assistant=None, repository=None):
        if assistant is not None:
            app.dependency_overrides[get_help_assistant] = lambda: assistant
        if repository is not None:
            app.dependency_overrides[get_help_repository] = lambda: repository
        return TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()


class AskEndpointTest(ApiTestCase):
    def test_ask_returns_grounded_answer(self):
        assistant = StubAssistant()
        client = self.override(assistant=assistant)

        response = client.post("/api/help/ask", json={"question": "How do I move a change to QA?"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["needed_for_help_input"])
        self.assertEqual(body["answer"], ASK_RESPONSE.answer)
        self.assertEqual(body["citations"][0]["loio"], "aaa1")
        self.assertEqual(assistant.requests[0].question, "How do I move a change to QA?")

    def test_ask_rejects_empty_question(self):
        client = self.override(assistant=StubAssistant())
        self.assertEqual(client.post("/api/help/ask", json={"question": ""}).status_code, 422)

    def test_ask_rejects_out_of_range_max_documents(self):
        client = self.override(assistant=StubAssistant())
        response = client.post("/api/help/ask", json={"question": "x", "max_documents": 99})
        self.assertEqual(response.status_code, 422)

    def test_claude_failure_maps_to_502(self):
        client = self.override(assistant=StubAssistant(error=ClaudeServiceError("declined")))
        response = client.post("/api/help/ask", json={"question": "x"})
        self.assertEqual(response.status_code, 502)
        self.assertIn("declined", response.json()["detail"])

    def test_unexpected_failure_maps_to_500(self):
        client = self.override(assistant=StubAssistant(error=RuntimeError("mongo down")))
        response = client.post("/api/help/ask", json={"question": "x"})
        self.assertEqual(response.status_code, 500)
        self.assertIn("mongo down", response.json()["detail"])


class DocumentEndpointTest(ApiTestCase):
    def test_list_documents(self):
        client = self.override(repository=StubRepository())
        body = client.get("/api/help/documents?limit=5").json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["limit"], 5)
        self.assertEqual(body["documents"][0]["loio"], "aaa1")

    def test_get_document_found_and_missing(self):
        client = self.override(repository=StubRepository())
        self.assertEqual(client.get("/api/help/documents/aaa1:en-US").status_code, 200)
        self.assertEqual(client.get("/api/help/documents/nope").status_code, 404)

    def test_search_documents(self):
        client = self.override(repository=StubRepository())
        body = client.get("/api/help/search?q=transport").json()
        self.assertEqual(body["query"], "transport")
        self.assertEqual(body["count"], 1)

    def test_search_requires_query(self):
        client = self.override(repository=StubRepository())
        self.assertEqual(client.get("/api/help/search").status_code, 422)

    def test_products_and_stats(self):
        client = self.override(repository=StubRepository())
        self.assertEqual(client.get("/api/help/products").json()["count"], 1)
        stats = client.get("/api/help/stats").json()
        self.assertEqual(stats["documents"], 1)
        self.assertEqual(stats["document_types"][0]["document_type"], "Topic")


class HealthEndpointTest(ApiTestCase):
    def test_health_ok(self):
        client = self.override(repository=StubRepository())
        body = client.get("/api/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["database"]["documents"], 1)

    def test_health_degraded_when_database_errors(self):
        client = self.override(repository=StubRepository(error=RuntimeError("no mongo")))
        body = client.get("/api/health").json()
        self.assertEqual(body["status"], "degraded")
        self.assertIn("no mongo", body["database"]["detail"])


if __name__ == "__main__":
    unittest.main()
