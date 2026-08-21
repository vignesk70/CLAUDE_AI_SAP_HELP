# Claude Support SAP AI

An AI-powered SAP support assistant that leverages Claude to help with SAP development, configuration, and troubleshooting.

## Overview

Claude Support SAP AI provides an intelligent interface for interacting with SAP systems, enabling developers and administrators to:

- Diagnose and resolve SAP configuration issues
- Generate and review ABAP code
- Troubleshoot common SAP errors and performance bottlenecks
- Get contextual guidance on SAP modules and transactions

## Tech Stack

- **Backend:** Python 3.11+ with FastAPI
- **AI Engine:** Anthropic Claude API (`anthropic` SDK)
- **Database:** MongoDB (`pymongo`)
- **Configuration:** pydantic-settings with `.env` files
- **Frontend:** React (planned — see `frontend/`)

## Getting Started

### Prerequisites

- Python 3.11 or higher
- MongoDB 6.0 or higher reachable at `MONGODB_URI`
- An Anthropic API key ([get one here](https://console.anthropic.com/))
- pip or a virtual environment manager (venv, conda, etc.)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd Claude_SupportSAP_AI

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` and set your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Optional settings you can override:

| Variable         | Default               | Description                      |
|------------------|-----------------------|----------------------------------|
| `CLAUDE_MODEL`   | `claude-sonnet-4-5`   | Claude model identifier          |
| `MAX_TOKENS`     | `1024`                | Maximum tokens per response      |
| `HOST`           | `0.0.0.0`            | Server bind address              |
| `PORT`           | `8000`                | Server port                      |
| `MONGODB_URI`    | `mongodb://localhost:27017/claude_sap_ai` | MongoDB connection string |
| `MONGODB_DATABASE` | `claude_sap_ai`     | MongoDB database name            |
| `SAP_HELP_SEARCH_URL` | `https://help.sap.com/http.svc/elasticsearch` | Endpoint the seeder queries |

### Database setup

The `help` collection holds SAP Help Portal topics harvested from
[help.sap.com/docs](https://help.sap.com/docs/). Create and populate it with:

```bash
python -m scripts.seed_help --refresh
```

That fetches fresh topics from the SAP Help Portal, rewrites the fixture at
`data/help_seed.json`, and upserts every topic into MongoDB. The collection and
its indexes are created on first run — no manual `mongosh` step needed.

Subsequent runs replay the committed fixture without touching the network:

```bash
python -m scripts.seed_help              # replay data/help_seed.json
python -m scripts.seed_help --drop       # wipe the collection first
python -m scripts.seed_help --refresh --limit 50
python -m scripts.seed_help --refresh --query "SAP Fiori elements" --query "IDoc"
```

Seeding is idempotent: `_id` is `<loio>:<language>`, so reruns update in place.
`python -m scripts.fetch_sap_help` regenerates the fixture without seeding.

**Document shape** (see `app/models/help.py`):

```json
{
  "_id": "496dd46f53523e90e10000000a42189c:en-US",
  "loio": "496dd46f53523e90e10000000a42189c",
  "title": "ABAP",
  "description": "",
  "snippet": "The ABAP command introduces a block of ABAP statements. …",
  "url": "https://help.sap.com/docs/ABAP_PLATFORM_NEW/c666.../496d....html",
  "product": "ABAP platform",
  "product_id": "ABAP_PLATFORM_NEW",
  "version": "2025 FPS01 (Feb 2026)",
  "version_id": "202510.001",
  "deliverable_title": "eCATT: Extended Computer Aided Test Tool (BC-TWB-TST-ECA)",
  "document_type": "Topic",
  "mime_type": "text/html",
  "language": "en-US",
  "state": "PRODUCTION",
  "published_at": "2026-07-27",
  "search_queries": ["ABAP"],
  "source": "help.sap.com",
  "fetched_at": "2026-08-21T08:08:36Z",
  "seeded_at": "2026-08-21T08:09:18Z"
}
```

**Indexes:** `loio_language`, `product_id`, `document_type`, and a `help_fulltext`
text index over `title`, `description`, and `snippet`:

```python
collection.find({"$text": {"$search": "transport request"}})
```

### Usage

Start the development server:

```bash
python -m app.main
```

The API will be available at `http://localhost:8000`.

**Interactive API docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/help/ask` | Ask a question — Claude routes, the `help` collection grounds the answer |
| `POST` | `/api/chat` | Raw Claude pass-through, no retrieval |
| `GET`  | `/api/help/search` | Full-text search the corpus directly |
| `GET`  | `/api/help/documents` | Page through topics (`product_id`, `document_type`, `skip`, `limit`) |
| `GET`  | `/api/help/documents/{id}` | One topic by `<loio>:<language>` |
| `GET`  | `/api/help/products` | Product facet counts |
| `GET`  | `/api/help/stats` | Corpus size plus product and document-type facets |
| `GET`  | `/api/health` | API, database, and corpus status |

### How `/api/help/ask` works

```
question
  |- ClaudeService.triage -----------------> HelpTriage (structured)
       needed_for_help_input = false -----> return triage.direct_answer, done
       needed_for_help_input = true  -----> HelpRepository.search_many(triage.search_queries)
                                              no hits --> say so + print the seed command
                                              hits -----> ClaudeService.answer_from_documents
                                                            |-> GroundedAnswer (structured)
```

Claude never sees the database and never writes free-form JSON. Both passes use
`client.messages.parse(output_format=...)`, so the Pydantic models in
[app/models/chat.py](app/models/chat.py) *are* the schema Claude must satisfy:
`HelpTriage` for the routing decision, `GroundedAnswer` for the cited answer.

Two retrieval details worth knowing:

- **Products boost, they do not filter.** Claude names SAP products freely, and a
  wrong guess used as a hard `AND` returns confidently irrelevant documents. A
  product match multiplies the text score instead (`PRODUCT_BOOST`). `rank_score`
  in the response is the boosted score, and it is what ordering uses.
- **A relevance floor is applied.** MongoDB `$text` OR-matches every term, so weak
  hits are always present. Merged results scoring below `RELEVANCE_FLOOR` of the
  best hit are dropped. `GET /api/help/search` skips both behaviours — its
  `product` filter is a real filter, because it comes from the caller rather than
  from the model.

**Ask:**

```bash
curl -X POST http://localhost:8000/api/help/ask   -H "Content-Type: application/json"   -d '{"question": "How do I analyse a short dump in ABAP?", "max_documents": 4}'
```

```json
{
  "question": "How do I analyse a short dump in ABAP?",
  "needed_for_help_input": true,
  "reasoning": "Short dump analysis is an SAP-specific procedure...",
  "search_queries": ["short dump analysis ABAP", "ST22 transaction"],
  "answer": "To analyse a short dump you use the ABAP Dump Analysis tool, transaction ST22...",
  "citations": [
    {"loio": "4b6d5f", "title": "ABAP Dump Analysis (ST22)", "url": "https://help.sap.com/docs/..."}
  ],
  "confidence": "medium",
  "followup_questions": ["How do I keep a dump beyond the retention period?"],
  "retrieved_documents": [
    {
      "id": "4b6d5f:en-US",
      "loio": "4b6d5f",
      "title": "ABAP Dump Analysis",
      "url": "https://help.sap.com/docs/...",
      "product": "ABAP platform",
      "score": 6.11,
      "rank_score": 9.77,
      "matched_query": "short dump analysis ABAP"
    }
  ],
  "model": "claude-opus-5"
}
```

`confidence` is `low` when the retrieved documents do not cover the question — the
answer then says what is missing instead of filling the gap with unsourced recall.

**Conversation turns** — prior turns go in `history` and are forwarded to both
Claude passes:

```bash
curl -X POST http://localhost:8000/api/help/ask   -H "Content-Type: application/json"   -d '{
    "question": "And how do I keep one for longer?",
    "history": [
      {"role": "user", "content": "How do I analyse a short dump?"},
      {"role": "assistant", "content": "Use transaction ST22."}
    ]
  }'
```

**Raw chat (no retrieval):**

```bash
curl -X POST http://localhost:8000/api/chat   -H "Content-Type: application/json"   -d '{"messages": [{"role": "user", "content": "What is transaction SM37?"}]}'
```

**Direct search and health:**

```bash
curl "http://localhost:8000/api/help/search?q=CDS+view+entity&limit=5"
curl http://localhost:8000/api/health
```

## Testing

```bash
python -m unittest discover -s tests -t .
```

The repository tests run against a throwaway `claude_sap_ai_test` database and skip
themselves when MongoDB is unreachable. Everything else is offline: Claude and Mongo
are replaced with stubs via FastAPI dependency overrides.

## Project Structure

```
Claude_SupportSAP_AI/
├── app/                        # Backend (FastAPI)
│   ├── main.py                 # Application entry point
│   ├── config.py               # Settings & environment config
│   ├── routers/
│   │   ├── chat.py             # Chat & health endpoints
│   │   └── help.py             # Ask + corpus endpoints
│   ├── dependencies.py         # FastAPI dependency providers
│   ├── services/
│   │   ├── claude_service.py   # Claude calls: chat, triage, grounded answer
│   │   └── help_assistant.py   # Ask orchestration: triage → retrieve → answer
│   ├── repositories/
│   │   └── help_repository.py  # Every `help` collection query lives here
│   ├── db/
│   │   └── mongo.py            # Async Mongo client & index setup
│   └── models/
│       ├── help.py             # `help` collection schema
│       └── chat.py             # Ask I/O + the schemas Claude must return
├── scripts/
│   ├── fetch_sap_help.py       # Harvest topics from help.sap.com
│   └── seed_help.py            # Seed / re-seed the `help` collection
├── data/
│   └── help_seed.json          # Committed seed fixture
├── tests/                      # Unit + repository integration tests
├── frontend/                   # Frontend (planned)
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .gitignore
└── README.md
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

## License

MIT
