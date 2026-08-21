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

**Example request:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "How do I check the status of a background job in SAP?"}
    ]
  }'
```

**Health check:**

```bash
curl http://localhost:8000/api/health
```

## Project Structure

```
Claude_SupportSAP_AI/
├── app/                        # Backend (FastAPI)
│   ├── main.py                 # Application entry point
│   ├── config.py               # Settings & environment config
│   ├── routers/
│   │   └── chat.py             # Chat & health API endpoints
│   ├── services/
│   │   └── claude_service.py   # Claude API integration
│   ├── db/
│   │   └── mongo.py            # MongoDB clients & index setup
│   └── models/
│       └── help.py             # `help` collection schema
├── scripts/
│   ├── fetch_sap_help.py       # Harvest topics from help.sap.com
│   └── seed_help.py            # Seed / re-seed the `help` collection
├── data/
│   └── help_seed.json          # Committed seed fixture
├── tests/                      # Unit tests (python -m unittest discover -s tests)
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
