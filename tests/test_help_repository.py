"""Integration tests for HelpRepository against the local MongoDB.

Uses a throwaway database (`<db>_test`) so the seeded corpus is never touched.
Skipped when MongoDB is unreachable.
"""

import unittest
from datetime import datetime, timezone

from pymongo.errors import PyMongoError

from app.config import settings
from app.db.mongo import close_client, get_client
from app.models.help import HelpDocument
from app.repositories.help_repository import HelpRepository

TEST_DB = f"{settings.mongodb_database}_test"


def make_document(loio: str, title: str, product: str, snippet: str = "") -> HelpDocument:
    return HelpDocument(
        _id=HelpDocument.make_id(loio, "en-US"),
        loio=loio,
        title=title,
        description="",
        snippet=snippet,
        url=f"https://help.sap.com/docs/{loio}.html",
        product=product,
        product_id=product.replace(" ", "_").upper(),
        document_type="Topic",
        published_at="2026-01-01",
        search_queries=["seed"],
        fetched_at=datetime.now(timezone.utc),
    )


FIXTURES = [
    make_document(
        "aaa1", "Creating a transport request", "SAP S/4HANA", "Use STMS to release transports."
    ),
    make_document(
        "bbb2", "CDS view entity syntax", "ABAP platform", "DEFINE VIEW ENTITY replaces DDIC views."
    ),
    make_document(
        "ccc3", "ST22 short dump analysis", "ABAP platform", "Analyse runtime errors in ST22."
    ),
]


class HelpRepositoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repository = HelpRepository(database=get_client()[TEST_DB])
        try:
            await self.repository.drop()
            await self.repository.upsert_many(FIXTURES)
        except PyMongoError as exc:
            self.skipTest(f"MongoDB unavailable: {exc}")

    async def asyncTearDown(self) -> None:
        await self.repository.drop()
        # Each test gets a fresh event loop, so its client must be released with it.
        await close_client()

    async def test_upsert_is_idempotent(self):
        stats = await self.repository.upsert_many(FIXTURES)
        self.assertEqual(stats["inserted"], 0)
        self.assertEqual(stats["total"], len(FIXTURES))

    async def test_get_by_id_and_loio(self):
        self.assertEqual((await self.repository.get("aaa1:en-US"))["title"], FIXTURES[0].title)
        self.assertEqual((await self.repository.get_by_loio("bbb2"))["loio"], "bbb2")
        self.assertIsNone(await self.repository.get("missing:en-US"))

    async def test_list_filters_by_product_id(self):
        documents = await self.repository.list(product_id="ABAP_PLATFORM")
        self.assertEqual({d["loio"] for d in documents}, {"bbb2", "ccc3"})
        self.assertEqual(await self.repository.count(product_id="ABAP_PLATFORM"), 2)

    async def test_search_ranks_by_text_score(self):
        documents = await self.repository.search("transport request")
        self.assertTrue(documents)
        self.assertEqual(documents[0]["loio"], "aaa1")
        self.assertIn("score", documents[0])

    async def test_search_filters_by_product(self):
        self.assertEqual(await self.repository.search("view entity", products=["SAP S/4HANA"]), [])
        hits = await self.repository.search("view entity", products=["ABAP platform"])
        self.assertEqual([d["loio"] for d in hits], ["bbb2"])

    async def test_search_falls_back_to_title_regex(self):
        # "ST22" is a transaction code the text index tokenises poorly on its own.
        documents = await self.repository.search("ST22")
        self.assertEqual([d["loio"] for d in documents], ["ccc3"])

    async def test_search_empty_query_returns_nothing(self):
        self.assertEqual(await self.repository.search("   "), [])

    async def test_search_many_merges_and_tags_queries(self):
        documents = await self.repository.search_many(["transport request", "view entity"])
        by_loio = {d["loio"]: d for d in documents}
        self.assertEqual(set(by_loio), {"aaa1", "bbb2"})
        self.assertEqual(by_loio["aaa1"]["matched_query"], "transport request")
        self.assertEqual(by_loio["bbb2"]["matched_query"], "view entity")

    async def test_search_many_respects_limit_and_blank_queries(self):
        self.assertEqual(await self.repository.search_many(["", "  "]), [])
        documents = await self.repository.search_many(
            ["transport", "view", "dump"], limit=2, relevance_floor=0
        )
        self.assertLessEqual(len(documents), 2)

    async def test_search_many_boosts_matching_product_without_filtering(self):
        # "transports" and "views" both match; the boost decides which leads.
        queries = ["transports", "views"]
        plain = await self.repository.search_many(queries, relevance_floor=0)
        boosted = await self.repository.search_many(
            queries, boost_products=["ABAP platform"], relevance_floor=0
        )
        self.assertEqual({d["loio"] for d in plain}, {d["loio"] for d in boosted})
        self.assertEqual(boosted[0]["product"], "ABAP platform")
        self.assertGreater(boosted[0]["rank_score"], boosted[0]["score"])

    async def test_search_many_boost_for_unknown_product_changes_nothing(self):
        queries = ["transports", "views"]
        plain = await self.repository.search_many(queries, relevance_floor=0)
        boosted = await self.repository.search_many(
            queries, boost_products=["No Such Product"], relevance_floor=0
        )
        self.assertEqual([d["loio"] for d in plain], [d["loio"] for d in boosted])

    async def test_relevance_floor_drops_weak_hits(self):
        # An OR query where one document matches strongly and others barely do.
        queries = ["transport request STMS release"]
        unfiltered = await self.repository.search_many(queries, relevance_floor=0)
        filtered = await self.repository.search_many(queries, relevance_floor=0.9)
        self.assertGreaterEqual(len(unfiltered), len(filtered))
        self.assertEqual(filtered[0]["loio"], "aaa1")

    async def test_product_and_type_facets(self):
        products = {p["product"]: p["count"] for p in await self.repository.products()}
        self.assertEqual(products["ABAP platform"], 2)
        types = {t["document_type"]: t["count"] for t in await self.repository.document_types()}
        self.assertEqual(types["Topic"], 3)

    async def test_indexes_created(self):
        names = await self.repository.ensure_indexes()
        self.assertIn("help_fulltext", names)
        self.assertIn("loio_language", names)


if __name__ == "__main__":
    unittest.main()
