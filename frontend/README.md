# Frontend — Claude Support SAP AI

A chat interface for the SAP support assistant, built with **Nuxt 4** and **Nuxt UI 4** (Tailwind CSS v4). It talks to the FastAPI backend in `../app`.

## Stack

- **Framework:** Nuxt 4 (SSR + auto-imports)
- **UI:** Nuxt UI 4 (Reka UI components + Tailwind CSS v4)
- **Icons:** `@iconify-json/lucide`
- **Theme:** dark by default, with a light/dark toggle

## Prerequisites

1. **Node.js 20+** and npm.
2. The **FastAPI backend running** on `http://localhost:8000` (see the root `README.md`). The frontend calls `POST /api/chat`.

## Setup

```bash
cd frontend
npm install
```

## Run

```bash
npm run dev
```

The dev server starts on `http://localhost:3000`. If that port is busy, Nuxt falls back to the next free port (check the terminal output — it may be `3003`).

> The backend must allow the frontend's origin via CORS. `app/main.py` already permits `localhost:3000` and `localhost:3003`.

## Configuration

The backend base URL is set in `nuxt.config.ts` under `runtimeConfig.public.apiBase` (default `http://localhost:8000`).

Override it without editing code via an environment variable:

```bash
NUXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

## How it connects to the backend

`app/composables/useChat.ts` sends the conversation to `POST {apiBase}/api/chat`:

```json
{ "messages": [{ "role": "user", "content": "..." }] }
```

and reads the assistant reply from `{ "reply": "..." }`.

## Project structure

```
frontend/
├── app/
│   ├── app.vue                     # Root — wraps pages in <UApp>
│   ├── assets/css/main.css         # Design system: primary palette + component classes
│   ├── pages/index.vue             # Chat page (auto-scroll, error banner)
│   ├── components/
│   │   ├── AppHeader.vue           # Title, new-chat, theme toggle
│   │   ├── ChatMessage.vue         # User/assistant message bubble
│   │   ├── ChatInput.vue           # Auto-resizing textarea + send button
│   │   ├── EmptyState.vue          # Welcome + suggestion prompts
│   │   └── TypingIndicator.vue     # Animated "Claude is thinking" dots
│   └── composables/useChat.ts      # Chat state + backend calls
├── nuxt.config.ts
└── package.json
```

## Extending the design

- **Colors / fonts:** edit the `@theme static` block in `app/assets/css/main.css`. The brand color is the `--color-primary-*` scale.
- **Reusable styles:** `.bubble-user`, `.bubble-assistant`, and `.suggestion-chip` live in the `@layer components` section of the same file.
