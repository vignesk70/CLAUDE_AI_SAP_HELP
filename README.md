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
- **Configuration:** pydantic-settings with `.env` files
- **Frontend:** React (planned — see `frontend/`)

## Getting Started

### Prerequisites

- Python 3.11 or higher
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
│   └── services/
│       └── claude_service.py   # Claude API integration
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
