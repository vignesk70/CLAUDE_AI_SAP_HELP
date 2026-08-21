"""MongoDB access layer.

Exposes a lazily-created synchronous client (used by CLI tooling such as the
seeder) and an async client (used by the FastAPI request handlers).
"""

from __future__ import annotations

from functools import lru_cache

from pymongo import AsyncMongoClient, MongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.database import Database

from app.config import settings

HELP_COLLECTION = "help"


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    """Return a process-wide synchronous MongoClient."""
    return MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)


@lru_cache(maxsize=1)
def get_async_client() -> AsyncMongoClient:
    """Return a process-wide asynchronous MongoClient."""
    return AsyncMongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)


def get_database() -> Database:
    """Return the configured database via the synchronous client."""
    return get_client()[settings.mongodb_database]


def get_async_database() -> AsyncDatabase:
    """Return the configured database via the asynchronous client."""
    return get_async_client()[settings.mongodb_database]


def ensure_help_indexes(database: Database | None = None) -> list[str]:
    """Create the indexes the `help` collection relies on. Idempotent.

    Returns:
        The names of the indexes that exist after the call.
    """
    db = database if database is not None else get_database()
    collection = db[HELP_COLLECTION]
    collection.create_index([("loio", 1), ("language", 1)], name="loio_language")
    collection.create_index("product_id", name="product_id")
    collection.create_index("document_type", name="document_type")
    collection.create_index(
        [("title", "text"), ("description", "text"), ("snippet", "text")],
        name="help_fulltext",
        default_language="english",
        # `language` holds a locale (en-US), which Mongo rejects as a text-index
        # language override, so point the override at an unused field name.
        language_override="text_language",
    )
    return sorted(collection.index_information())
