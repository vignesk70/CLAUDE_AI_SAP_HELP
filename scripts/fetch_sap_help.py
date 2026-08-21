"""Fetch SAP Help Portal topics and normalise them into `help` documents.

The portal front end (https://help.sap.com/docs/) is a single-page app; the
underlying search service it calls is used here instead:

    GET https://help.sap.com/http.svc/elasticsearch?q=<query>&...

Run this module to (re)generate the seed fixture:

    python -m scripts.fetch_sap_help --out data/help_seed.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.config import settings
from app.models.help import HelpDocument

BASE_URL = "https://help.sap.com"
USER_AGENT = "claude-sap-ai-seeder/0.1 (+https://help.sap.com/docs)"

#: Topics seeded by default. Broad enough to cover the assistant's subject areas.
DEFAULT_QUERIES: tuple[str, ...] = (
    "ABAP",
    "ABAP RESTful Application Programming Model",
    "CDS view entity",
    "SAP BTP Cloud Foundry",
    "SAP Cloud Application Programming Model",
    "SAP Fiori elements",
    "SAP HANA Cloud",
    "SAP S/4HANA transport request",
    "background job scheduling",
    "IDoc processing",
    "BAPI remote function call",
    "OData service registration",
    "SAP authorization object",
    "SAP workflow",
    "performance trace ST12",
    "short dump analysis ST22",
)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_text(raw: str | None) -> str:
    """Strip the highlight markup SAP returns and collapse whitespace."""
    if not raw:
        return ""
    text = _TAG_RE.sub("", raw)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def absolute_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return urllib.parse.urljoin(BASE_URL, url)


def normalise_result(result: dict[str, Any], query: str) -> HelpDocument | None:
    """Map one search hit onto a `HelpDocument`, or None if it is unusable."""
    loio = (result.get("loio") or "").strip()
    title = clean_text(result.get("title"))
    url = absolute_url(result.get("url") or "")
    if not loio or not title or not url:
        return None

    language = (result.get("language") or "en-US").strip() or "en-US"
    return HelpDocument(
        _id=HelpDocument.make_id(loio, language),
        loio=loio,
        title=title,
        description=clean_text(result.get("description")),
        snippet=clean_text(result.get("snippet")),
        url=url,
        product=clean_text(result.get("product")),
        product_id=(result.get("productId") or "").strip(),
        version=clean_text(result.get("version")),
        version_id=(result.get("versionId") or "").strip(),
        deliverable_title=clean_text(result.get("deliverableTitle")),
        document_type=(result.get("documentType") or "").strip(),
        mime_type=(result.get("mimeType") or "").strip(),
        language=language,
        state=(result.get("state") or "").strip(),
        published_at=(result.get("date") or "").strip(),
        search_queries=[query],
        fetched_at=datetime.now(timezone.utc),
    )


def merge(documents: Iterable[HelpDocument]) -> list[HelpDocument]:
    """De-duplicate by `_id`, keeping the union of the queries that found each doc."""
    merged: dict[str, HelpDocument] = {}
    for doc in documents:
        existing = merged.get(doc.id)
        if existing is None:
            merged[doc.id] = doc
            continue
        for query in doc.search_queries:
            if query not in existing.search_queries:
                existing.search_queries.append(query)
    return list(merged.values())


def search(query: str, limit: int = 20, timeout: int = 30) -> list[dict[str, Any]]:
    """Call the SAP Help Portal search service for a single query."""
    params = {
        "area": "content",
        "version": "",
        "language": "en-US",
        "state": "PRODUCTION",
        "q": query,
        "transtype": "standard,html,pdf,others",
        "product": "",
        "to": str(limit),
        "advancedSearch": "0",
        "excludeNotSearchable": "1",
    }
    url = f"{settings.sap_help_search_url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") != "OK":
        raise RuntimeError(f"SAP Help search failed for {query!r}: {payload.get('status')}")
    return payload.get("data", {}).get("results", []) or []


def fetch(
    queries: Iterable[str] = DEFAULT_QUERIES,
    limit: int = 20,
    delay: float = 0.5,
) -> list[HelpDocument]:
    """Fetch and normalise topics for every query. Failed queries are skipped."""
    collected: list[HelpDocument] = []
    for index, query in enumerate(queries):
        if index and delay:
            time.sleep(delay)
        try:
            results = search(query, limit=limit)
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            print(f"  ! {query}: {type(exc).__name__}: {exc}")
            continue
        documents = [doc for doc in (normalise_result(r, query) for r in results) if doc]
        print(f"  + {query}: {len(documents)} topics")
        collected.extend(documents)
    return merge(collected)


def write_fixture(documents: list[HelpDocument], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": BASE_URL + "/docs/",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(documents),
        "documents": [doc.model_dump(by_alias=True, mode="json") for doc in documents],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate the SAP help seed fixture.")
    parser.add_argument(
        "--out", type=Path, default=Path("data/help_seed.json"), help="Fixture output path"
    )
    parser.add_argument("--limit", type=int, default=20, help="Results per query")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between queries")
    parser.add_argument(
        "--query", action="append", dest="queries", help="Override the query list (repeatable)"
    )
    args = parser.parse_args()

    queries = args.queries or list(DEFAULT_QUERIES)
    print(f"Fetching {len(queries)} queries from {settings.sap_help_search_url}")
    documents = fetch(queries, limit=args.limit, delay=args.delay)
    write_fixture(documents, args.out)
    print(f"Wrote {len(documents)} unique topics to {args.out}")


if __name__ == "__main__":
    main()
