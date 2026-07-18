# AI Agent Lab

[English](README.md) | [中文](README_CN.md)

AI Agent Lab is a staged AI Engineering Workspace for learning and building the core systems behind modern AI applications. It starts with a stable FastAPI + React foundation and grows through chat, provider abstraction, tool calling, RAG, traceability, memory, agent runtime, MCP, voice, vision, and desktop workflows.

This repository is not a collection of disconnected demos. The goal is to build a usable, observable, testable, and extensible AI engineering workspace one plan at a time.

## Current Stage

Current release: `v0.1.0` (Plan 1 foundation).

Plan 1 covers:

- Project foundation
- FastAPI backend skeleton
- React + TypeScript frontend skeleton
- Basic health check
- Basic chat workflow
- LLM provider abstraction
- OpenAI-compatible provider support
- Streaming chat
- Conversation history
- Basic token, cost, latency, logging, and error handling

Completed scope: `P1-M1-S1` through `P1-M4-S8`.

Current development stage: Plan 2 M2 `read_file` is complete. Completed Plan 2
scope: `P2-M1-S1` through `P2-M2-S3`.

The M1 foundation includes Tool and ToolResult contracts, ToolCall transport
schemas, an ordered Tool Registry, Draft 2020-12 argument validation, read-only
path policy, and AgentRun/ToolCall ORM models with an Alembic migration. The
first executable built-in Tool safely reads workspace-relative UTF-8 text,
rejects files over 1 MiB, truncates output after 100,000 characters with
metadata, returns safe failures, and registers into a caller-owned Registry. It
does not yet include `list_dir`, Provider tool calling, an Agent Loop, Agent
APIs, or frontend Agent/ToolCall views.

Next batch: `P2-M2-S4` through `P2-M2-S6`.

## v0.1.0 Demo

![Desktop Chat workspace](docs/assets/plan1/chat-workspace-desktop.png)

![Mobile Chat workspace](docs/assets/plan1/chat-workspace-mobile.png)

These are sanitized mock demonstrations. No live Provider, real API key, or
user-local conversation database was used to create them.

## Non-Goals For Plan 1

Plan 1 does not implement:

- Tool Calling
- RAG
- Memory
- MCP
- Voice
- Vision
- Desktop app
- Multi-agent workflows

Those capabilities are intentionally deferred to later plans.

## Planned Stack

- Backend: Python 3.11, FastAPI, Pydantic, SQLAlchemy, SQLite
- Frontend: React, Vite, TypeScript
- LLM access: OpenAI-compatible providers, such as DeepSeek or OpenRouter
- Testing: pytest for backend, TypeScript/build checks for frontend

The workspace is local-first and primarily single-user. SQLite is the default
and long-term supported primary database, not a temporary stop before
PostgreSQL. SQLAlchemy and Alembic preserve reasonable database portability,
but PostgreSQL remains an optional compatibility path only if deployment or
concurrency requirements materially change.

## Repository Layout

```text
AI-Agent-Lab/
├── backend/       # FastAPI backend, added incrementally during Plan 1
├── frontend/      # React + TypeScript frontend, added incrementally during Plan 1
├── docs/          # Tracked project documentation and sanitized assets
├── docs-plan/     # Tracked source planning documents and execution tables
├── docs-local/    # Ignored local drafts, private notes, and sensitive materials
├── AGENTS.md      # Root collaboration rules
├── AGENTS_CN.md   # Root Chinese collaboration rules
├── .env.example   # Root environment variable example
└── .gitignore
```

## Documentation Boundaries

- `docs-plan/` contains plan source documents and execution step tables. It is tracked.
- `docs/` contains formal project documentation and sanitized verification assets. It is tracked.
- `docs-local/` contains local drafts, private notes, temporary review material, and sensitive screenshots. It is ignored.

## Local Development

The Plan 1 backend and frontend can be started independently. The root
`.env.example` is a workspace-level reference and is not loaded automatically
by either application. Copy the service-specific examples when local overrides
are needed:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Backend commands run from `backend/` read `backend/.env`; Vite commands run
from `frontend/` read `frontend/.env`. Keep those local files untracked. The
tracked examples contain no real credentials, and the frontend `VITE_*`
variables must never contain secrets because Vite exposes them to the browser.

### Backend

```bash
py -3.11 -m venv .venv
cd backend
..\.venv\Scripts\python.exe -m pip install -e .[dev] --no-build-isolation
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

The backend defaults to `sqlite:///./ai_agent_lab.db`. Override it with
`DATABASE_URL` in a local untracked environment file when needed. Alembic owns
schema creation and currently creates `conversations`, `messages`, and
`llm_calls`; the application does not create tables during startup.

The OpenAI-compatible Provider reads these optional environment settings when
it is initialized:

```text
OPENAI_COMPATIBLE_BASE_URL=https://api.example.com/v1
OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_MODEL=example-model
OPENAI_COMPATIBLE_TIMEOUT_SECONDS=30
```

Keep real values only in a local untracked `.env` file or environment
variables. The application can start without a key while it only serves the
health flow; attempting to initialize the Provider without a key raises a
readable configuration error. Batch 5 tests use mock HTTP and do not contact a
real model service.

The JSON Model Registry is stored at
`backend/app/providers/llm/models.json`. Its tracked entry is example
configuration only. Registry loading, filtering, lookup, duplicate detection,
and strict metadata validation are covered by unit tests. See
`docs/03-llm-provider.md` for Provider and Registry boundaries.

The non-streaming and SSE Chat backend flows are available:

```text
POST /api/v1/conversations
GET  /api/v1/conversations
GET  /api/v1/conversations/{conversation_id}
GET  /api/v1/conversations/{conversation_id}/messages
GET  /api/v1/models
POST /api/v1/chat/completions
POST /api/v1/chat/stream
```

The Chat endpoint accepts one new user `content` value. The backend owns and
loads persisted conversation history, validates the selected Registry model,
calls the configured Provider, and atomically stores the user message,
assistant message, and successful `LLMCall`. The SSE endpoint emits `delta`
events followed by one `done` event. A successful stream is committed before
`done`; Provider failure or client cancellation rolls back the entire turn.
Tests use mock Providers only.

The first successful user turn becomes the conversation title after whitespace
normalization and a 50-character limit. Successful turns also remember the
selected Registry model and advance conversation activity time. Conversation
and message list APIs support recent-history navigation; failed or cancelled
turns do not update this metadata.

Successful non-streaming and streaming turns persist Provider usage, Registry-
based estimated cost, and Provider latency on `LLMCall`. Missing usage or an
unknown Registry price remains `null`; the backend does not invent values.
HTTP and SSE failures use a safe structured error envelope linked to a server-
generated `X-Request-ID`. Request and model-call logs include request ID,
provider/model, outcome, and latency without logging full message content,
credentials, upstream error bodies, or SQL parameters.

Health check:

```text
GET http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "ai-agent-lab-backend"
}
```

Backend verification:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL printed by `npm run dev`. The first screen is the Chat
workspace with API health, configured model identity, message states, streaming
output, Stop, and New Chat controls. The frontend reads these safe defaults:

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_DEFAULT_PROVIDER=openai_compatible
VITE_DEFAULT_MODEL=example-model
```

The API health area shows `Checking API`, `API connected`, or `API unavailable`.
Workspace initialization has a distinct loading state while models and recent
conversations load. If initialization fails, one readable error and a `Retry`
button are shown; a successful retry returns to the ready workspace without an
automatic retry loop. Once ready, Chat has empty, conversation-loading,
streaming, completed, stopped, and error states. The model selector is populated
from `GET /api/v1/models`; the sidebar loads recent conversations and their
persisted messages. The selected conversation is stored in
`?conversation=<uuid>`, so refreshing restores its messages and last successful
model. Stopping preserves partial text locally, but the interrupted turn is not
persisted. Late history and conversation-list refresh responses are ignored,
and a terminal SSE error actively releases the response reader.

Frontend checks:

```powershell
cd frontend
npm run typecheck
npm run test
npm run build
```

Release documentation:

- [Changelog](CHANGELOG.md)
- [Plan 1 foundation release](docs/02-plan-1-foundation.md)
- [Architecture](docs/01-architecture.md)
- [LLM Provider and Model Registry](docs/03-llm-provider.md)
- [Tool Calling design](docs/10-tool-calling-design.md)
- [Plan 1 final review record](docs/reviews/2026-07-13-plan1-v0.1.0-final-review.md)
- `docs-plan/00-ALL PLAN/01-PLAN-1 (V1.0).md`
- `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

## Known Limitations

Release verification uses mock Providers; it does not prove live
DeepSeek/OpenRouter connectivity. Usage, estimated cost, and latency are stored
on backend `LLMCall` records but are not displayed in the frontend. The current
editable-install workflow also leaves `models.json` out of future wheel/sdist
package data. Provider retry/fallback, failed-call audit rows, conversation
management extensions, Markdown rendering, and later-Plan features remain
deferred. See the [Plan 1 foundation release](docs/02-plan-1-foundation.md) for
the complete limitation list.

## Roadmap

- Plan 1: Project foundation + Basic Chat + LLM Providers
- Plan 2: Tool Calling + Simple Agent Loop
- Plan 3: Knowledge Base + Document Ingestion + Naive RAG
- Plan 4: Trace + Advanced RAG + Rerank + Evaluation
- Plan 5: Memory + Context Engine + Agent Runtime + Human Approval
- Plan 6: MCP + Voice + Vision + Desktop
