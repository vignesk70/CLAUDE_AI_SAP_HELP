"""Data access for the `help` collection.

All query logic for SAP help topics lives here — routers and services never
touch a Mongo collection directly.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterable

from pymongo import UpdateOne
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.db.mongo import HELP_COLLECTION, ensure_help_indexes, get_database
from app.models.help import HelpDocument

#: Fields returned by list/search reads. `snippet` is included because it is the
#: only body text the SAP search API gives us, and the RAG prompt needs it.
PROJECTION: dict[str, int] = {
    "loio": 1,
    "title": 1,
    "description": 1,
    "snippet": 1,
    "url": 1,
    "product": 1,
    "product_id": 1,
    "version": 1,
    "deliverable_title": 1,
    "document_type": 1,
    "language": 1,
    "published_at": 1,
}

#: A merged result must score at least this fraction of the best hit to survive.
RELEVANCE_FLOOR = 0.3

#: Multiplier applied when a document's product matches a requested product.
PRODUCT_BOOST = 1.6


class HelpRepository:
    """Async repository over the `help` collection."""

    def __init__(self, database: AsyncDatabase | None = None) -> None:
        self._database = database if database is not None else get_database()

    @property
    def collection(self) -> AsyncCollection:
        return self._database[HELP_COLLECTION]

    # ---------------------------------------------------------------- schema

    async def ensure_indexes(self) -> list[str]:
        """Create the collection's indexes if they are missing."""
        return await ensure_help_indexes(self._database)

    # ----------------------------------------------------------------- reads

    async def count(
        self, product_id: str | None = None, document_type: str | None = None
    ) -> int:
        return await self.collection.count_documents(
            build_filter(product_id=product_id, document_type=document_type)
        )

    async def get(self, document_id: str) -> dict[str, Any] | None:
        """Fetch one document by `_id` (`<loio>:<language>`)."""
        return await self.collection.find_one({"_id": document_id})

    async def get_by_loio(self, loio: str, language: str = "en-US") -> dict[str, Any] | None:
        return await self.collection.find_one({"loio": loio, "language": language})

    async def list(
        self,
        product_id: str | None = None,
        document_type: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List documents, newest publication first."""
        cursor = (
            self.collection.find(
                build_filter(product_id=product_id, document_type=document_type), PROJECTION
            )
            .sort([("published_at", -1), ("title", 1)])
            .skip(skip)
            .limit(limit)
        )
        return await cursor.to_list(length=limit)

    async def search(
        self,
        query: str,
        products: Iterable[str] | None = None,
        document_types: Iterable[str] | None = None,
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        """Full-text search over title/description/snippet, best match first.

        Falls back to a case-insensitive title match when the text index returns
        nothing: SAP titles are full of transaction codes the stemmer misses.
        """
        query = (query or "").strip()
        if not query:
            return []

        criteria: dict[str, Any] = {"$text": {"$search": query}}
        product_list = [p for p in (products or []) if p]
        if product_list:
            criteria["product"] = {"$in": product_list}
        type_list = [t for t in (document_types or []) if t]
        if type_list:
            criteria["document_type"] = {"$in": type_list}

        projection: dict[str, Any] = {**PROJECTION, "score": {"$meta": "textScore"}}
        cursor = (
            self.collection.find(criteria, projection)
            .sort([("score", {"$meta": "textScore"})])
            .limit(limit)
        )
        results = await cursor.to_list(length=limit)
        if results:
            return results
        # Drop $text but keep the product/type filters, so a fallback can never
        # return a document the caller filtered out.
        criteria.pop("$text")
        return await self.search_by_title(query, limit, extra=criteria)

    async def search_by_title(
        self, query: str, limit: int = 6, extra: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Regex fallback for terms the text index cannot stem (e.g. ST22)."""
        criteria: dict[str, Any] = {
            **(extra or {}),
            "title": {"$regex": re.escape(query), "$options": "i"},
        }
        cursor = self.collection.find(criteria, PROJECTION).limit(limit)
        return await cursor.to_list(length=limit)

    async def search_many(
        self,
        queries: Iterable[str],
        boost_products: Iterable[str] | None = None,
        limit: int = 6,
        per_query_limit: int | None = None,
        relevance_floor: float = RELEVANCE_FLOOR,
    ) -> list[dict[str, Any]]:
        """Run several searches and merge them, best-scoring first.

        `boost_products` re-ranks rather than filters. Product names supplied by
        a model are guesses, and a wrong guess used as a hard filter silently
        returns confidently irrelevant documents — use `search(products=...)`
        when the filter comes from the user instead.

        Each result is tagged with `matched_query`; documents found by more than
        one query keep their highest score. Results scoring below
        `relevance_floor` of the best hit are dropped: Mongo `$text` OR-matches
        every term, so weak hits are always present and always unhelpful.
        """
        cleaned = [q.strip() for q in queries if q and q.strip()]
        if not cleaned:
            return []

        boosted = {p for p in (boost_products or []) if p}
        per_query = per_query_limit or max(2, limit)
        merged: dict[str, dict[str, Any]] = {}
        for query in cleaned:
            for doc in await self.search(query, limit=per_query):
                score = _boosted_score(doc, boosted)
                existing = merged.get(doc["_id"])
                if existing is None or score > existing["rank_score"]:
                    merged[doc["_id"]] = {**doc, "matched_query": query, "rank_score": score}

        ranked = sorted(merged.values(), key=lambda d: d["rank_score"], reverse=True)
        if ranked and relevance_floor > 0:
            cutoff = ranked[0]["rank_score"] * relevance_floor
            ranked = [doc for doc in ranked if doc["rank_score"] >= cutoff]
        return ranked[:limit]

    async def products(self, limit: int = 50) -> list[dict[str, Any]]:
        """Product facet counts, largest first."""
        pipeline: list[dict[str, Any]] = [
            {"$match": {"product": {"$nin": ["", None]}}},
            {
                "$group": {
                    "_id": "$product",
                    "product_id": {"$first": "$product_id"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1, "_id": 1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "product": "$_id", "product_id": 1, "count": 1}},
        ]
        cursor = await self.collection.aggregate(pipeline)
        return await cursor.to_list(length=limit)

    async def document_types(self, limit: int = 50) -> list[dict[str, Any]]:
        """Document-type facet counts, largest first."""
        pipeline: list[dict[str, Any]] = [
            {"$match": {"document_type": {"$nin": ["", None]}}},
            {"$group": {"_id": "$document_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}},
            {"$limit": limit},
            {"$project": {"_id": 0, "document_type": "$_id", "count": 1}},
        ]
        cursor = await self.collection.aggregate(pipeline)
        return await cursor.to_list(length=limit)

    # ---------------------------------------------------------------- writes

    async def upsert_many(self, documents: list[HelpDocument]) -> dict[str, int]:
        """Upsert documents keyed on `_id`. Used by the seeder; idempotent."""
        await self.ensure_indexes()
        if not documents:
            return {"matched": 0, "inserted": 0, "modified": 0, "total": await self.count()}

        now = datetime.now(timezone.utc)
        operations = []
        for doc in documents:
            record = doc.model_dump(by_alias=True)
            doc_id = record.pop("_id")
            operations.append(
                UpdateOne({"_id": doc_id}, {"$set": {**record, "seeded_at": now}}, upsert=True)
            )

        result = await self.collection.bulk_write(operations, ordered=False)
        return {
            "matched": result.matched_count,
            "inserted": len(result.upserted_ids),
            "modified": result.modified_count,
            "total": await self.count(),
        }

    async def drop(self) -> None:
        """Drop the collection (indexes go with it)."""
        await self.collection.drop()


def _boosted_score(doc: dict[str, Any], boost_products: set[str]) -> float:
    """Text score, lifted when the document is in a product the caller favours."""
    score = float(doc.get("score") or 0.0)
    if boost_products and doc.get("product") in boost_products:
        score *= PRODUCT_BOOST
    return score


def build_filter(
    product_id: str | None = None, document_type: str | None = None
) -> dict[str, Any]:
    """Build the shared list/count filter."""
    criteria: dict[str, Any] = {}
    if product_id:
        criteria["product_id"] = product_id
    if document_type:
        criteria["document_type"] = document_type
    return criteria
