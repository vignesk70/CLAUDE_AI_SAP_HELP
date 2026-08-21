"""Seed the `help` collection in MongoDB.

    python -m scripts.seed_help                 # seed from data/help_seed.json
    python -m scripts.seed_help --refresh       # re-fetch from help.sap.com first
    python -m scripts.seed_help --drop          # wipe the collection, then seed

Seeding is idempotent: each document's `_id` is `<loio>:<language>`, so a rerun
updates in place instead of duplicating.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pymongo import UpdateOne

from app.db.mongo import HELP_COLLECTION, ensure_help_indexes, get_database
from app.models.help import HelpDocument
from scripts.fetch_sap_help import DEFAULT_QUERIES, fetch, write_fixture

FIXTURE_PATH = Path("data/help_seed.json")


def load_fixture(path: Path) -> list[HelpDocument]:
    """Read the seed fixture from disk."""
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run `python -m scripts.seed_help --refresh` to generate it."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [HelpDocument.model_validate(item) for item in payload["documents"]]


def upsert(documents: list[HelpDocument], drop: bool = False) -> dict[str, int]:
    """Upsert documents into the `help` collection and report what changed."""
    database = get_database()
    collection = database[HELP_COLLECTION]

    if drop:
        collection.drop()

    ensure_help_indexes(database)

    if not documents:
        return {"matched": 0, "inserted": 0, "modified": 0, "total": 0}

    now = datetime.now(timezone.utc)
    operations = []
    for doc in documents:
        record = doc.model_dump(by_alias=True)
        doc_id = record.pop("_id")
        operations.append(
            UpdateOne(
                {"_id": doc_id},
                {"$set": {**record, "seeded_at": now}},
                upsert=True,
            )
        )

    result = collection.bulk_write(operations, ordered=False)
    return {
        "matched": result.matched_count,
        "inserted": len(result.upserted_ids),
        "modified": result.modified_count,
        "total": collection.count_documents({}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the MongoDB `help` collection.")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch fresh data from help.sap.com and rewrite the fixture before seeding",
    )
    parser.add_argument(
        "--drop", action="store_true", help="Drop the collection before seeding"
    )
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH, help="Fixture path")
    parser.add_argument("--limit", type=int, default=20, help="Results per query on --refresh")
    parser.add_argument(
        "--query", action="append", dest="queries", help="Override query list on --refresh"
    )
    args = parser.parse_args()

    if args.refresh:
        queries = args.queries or list(DEFAULT_QUERIES)
        print(f"Refreshing fixture from help.sap.com ({len(queries)} queries)")
        documents = fetch(queries, limit=args.limit)
        if not documents:
            raise SystemExit("Refresh returned no documents; fixture left untouched.")
        write_fixture(documents, args.fixture)
        print(f"Wrote {len(documents)} topics to {args.fixture}")
    else:
        documents = load_fixture(args.fixture)
        print(f"Loaded {len(documents)} topics from {args.fixture}")

    stats = upsert(documents, drop=args.drop)
    print(
        f"help collection: inserted={stats['inserted']} "
        f"updated={stats['modified']} total={stats['total']}"
    )


if __name__ == "__main__":
    main()
