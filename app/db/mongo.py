"""MongoDB access layer.

One async client per event loop. `AsyncMongoClient` binds to the loop it was
created on and raises if reused from another, so the cache is keyed by loop
rather than being a plain singleton — a web server has one loop, but the seeder
(`asyncio.run`) and the test suite each create their own.
"""

from __future__ import annotations

import asyncio

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.config import settings

HELP_COLLECTION = "help"


_clients: dict[int, AsyncMongoClient] = {}


def _loop_key() -> int:
    """Identify the running loop; 0 when called outside one."""
    try:
        return id(asyncio.get_running_loop())
    except RuntimeError:
        return 0


def get_client() -> AsyncMongoClient:
    """Return the async MongoClient bound to the current event loop."""
    key = _loop_key()
    client = _clients.get(key)
    if client is None:
        client = AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
        _clients[key] = client
    return client


def get_database() -> AsyncDatabase:
    """Return the configured database."""
    return get_client()[settings.mongodb_database]


async def close_client() -> None:
    """Close and forget this loop's client (app shutdown, end of a seed run)."""
    client = _clients.pop(_loop_key(), None)
    if client is not None:
        await client.close()


async def ensure_help_indexes(database: AsyncDatabase | None = None) -> list[str]:
    """Create the indexes the `help` collection relies on. Idempotent.

    Returns:
        The names of the indexes that exist after the call.
    """
    db = database if database is not None else get_database()
    collection = db[HELP_COLLECTION]
    await collection.create_index([("loio", 1), ("language", 1)], name="loio_language")
    await collection.create_index("product_id", name="product_id")
    await collection.create_index("document_type", name="document_type")
    await collection.create_index(
        [("title", "text"), ("description", "text"), ("snippet", "text")],
        name="help_fulltext",
        default_language="english",
        # `language` holds a locale (en-US), which Mongo rejects as a text-index
        # language override, so point the override at an unused field name.
        language_override="text_language",
    )
    return sorted(await collection.index_information())
