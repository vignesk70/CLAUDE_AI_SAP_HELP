"""Seed the `help` collection in MongoDB.

    python -m scripts.seed_help                 # seed from data/help_seed.json
    python -m scripts.seed_help --refresh       # re-fetch from help.sap.com first
    python -m scripts.seed_help --drop          # wipe the collection, then seed

Seeding is idempotent: each document's `_id` is `<loio>:<language>`, so a rerun
updates in place instead of duplicating. Writes go through `HelpRepository`, the
same code path the API uses.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db.mongo import close_client
from app.models.help import HelpDocument
from app.repositories.help_repository import HelpRepository
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


async def seed(documents: list[HelpDocument], drop: bool = False) -> dict[str, int]:
    """Upsert documents into the `help` collection and report what changed."""
    repository = HelpRepository()
    if drop:
        await repository.drop()
    return await repository.upsert_many(documents)


async def run(args: argparse.Namespace) -> None:
    if args.refresh:
        queries = args.queries or list(DEFAULT_QUERIES)
        print(f"Refreshing fixture from help.sap.com ({len(queries)} queries)")
        documents = await asyncio.to_thread(fetch, queries, args.limit)
        if not documents:
            raise SystemExit("Refresh returned no documents; fixture left untouched.")
        write_fixture(documents, args.fixture)
        print(f"Wrote {len(documents)} topics to {args.fixture}")
    else:
        documents = load_fixture(args.fixture)
        print(f"Loaded {len(documents)} topics from {args.fixture}")

    try:
        stats = await seed(documents, drop=args.drop)
    finally:
        await close_client()

    print(
        f"help collection: inserted={stats['inserted']} "
        f"updated={stats['modified']} total={stats['total']}"
    )


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
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
