# Architecture

## Current Architecture Stage

This document describes the Plan 1 architecture target. The repository has completed `P1-M1-S1` through `P1-M2-S8`, so the health flow, frontend skeleton, database foundation, LLM Provider contract, OpenAI-compatible adapter, and JSON Model Registry exist. Later Plan 1 batches will add the chat flow, API-level streaming, persistence services, logging, and detailed error handling.

The first architectural goal is a thin, understandable web application foundation:

```text
React frontend -> FastAPI API routes -> services -> providers / database
```

API routes should remain thin. Validation belongs at the schema boundary, business logic belongs in services, and provider details stay behind provider adapters.

## Repository Structure

```text
AI-Agent-Lab/
├── backend/
│   └── app/
│       ├── main.py
│       ├── api/
│       ├── core/
│       ├── db/
│       ├── models/
│       ├── schemas/
│       ├── services/
│       └── providers/
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── pages/
│       └── types/
├── docs/
├── docs-plan/
└── docs-local/
```

The complete directory tree will be created incrementally. Plan 1 should not create future-plan modules before they are needed.

## Backend Boundaries

The backend uses FastAPI.

Expected Plan 1 backend layers:

| Layer | Responsibility |
|---|---|
| `api/` | HTTP routes and response shaping |
| `schemas/` | Pydantic request and response contracts |
| `services/` | Chat, conversation, and application logic |
| `providers/` | LLM provider abstractions and adapters |
| `db/` | SQLAlchemy session and database setup |
| `models/` | ORM models |
| `core/` | Config, logging, and error handling |

The first backend endpoint is implemented:

```text
GET /api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "ai-agent-lab-backend"
}
```

## Database Foundation

The current backend database layer uses SQLite, SQLAlchemy 2, and Alembic.
`DATABASE_URL` defaults to `sqlite:///./ai_agent_lab.db`, while schema creation
is owned by migrations rather than application startup.

SQLite is the default and long-term supported primary database for this
local-first, primarily single-user workspace. It is not a temporary database
that must be replaced after Plan 1. SQLAlchemy and Alembic should preserve
reasonable portability, but PostgreSQL is only an optional compatibility path
if the product later gains server deployment, multi-user access, or sustained
concurrent writes. Future modules should optimize for reliable local SQLite
operation without adding PostgreSQL-specific infrastructure preemptively.

The initial migration creates:

- `conversations`
- `messages`
- `llm_calls`

All model IDs use UUID v4 values. Datetimes are stored as timezone-naive UTC
values because SQLite does not preserve timezone information consistently.
Deleting a conversation cascades to its messages and LLM calls. Deleting an
individual message preserves its LLM call records and sets `message_id` to
`NULL`.

Foreign-key columns used by conversation and message lookups are indexed.
SQLAlchemy metadata uses a stable naming convention for primary keys, foreign
keys, indexes, unique constraints, and check constraints so future Alembic
migrations can reference schema objects predictably on SQLite.

The current schemas expose create and read contracts only. Service behavior,
HTTP routes, and conversation persistence workflows remain deferred to their
scheduled Plan 1 batches.

## Frontend Boundaries

The frontend uses React + Vite + TypeScript.

Expected Plan 1 frontend areas:

| Area | Responsibility |
|---|---|
| `src/api/` | API client wrappers |
| `src/types/` | Shared TypeScript types |
| `src/pages/` | Page-level views |
| `src/components/` | Feature and layout components |

The UI should feel like an engineering workspace: quiet, dense, readable, and practical. It should not become a marketing landing page.

Current Milestone 1 frontend code includes the base React app, `src/api/client.ts`, and `src/api/health.ts`. The home page calls `GET /api/v1/health` on load and renders loading, healthy, and error states. Page, component, and broader shared type directories will be added when the active step needs them.

## Plan 1 Data Flow

Plan 1 will evolve toward this flow:

```text
User message
-> Frontend chat UI
-> FastAPI chat route
-> Chat service
-> LLM provider adapter
-> Provider response or stream
-> Conversation persistence
-> Frontend message rendering
```

Streaming and persistence workflows are part of Plan 1, but they should be implemented in later Plan 1 batches after the provider and service layers exist.

## Provider Principle

External AI capabilities should be provider-based. Plan 1 starts with LLM providers only. Later plans will add other provider families, but they should not be implemented during Plan 1 unless the active step explicitly requires them.

Plan 1 provider target:

- `BaseLLMProvider` defines vendor-neutral asynchronous `chat` and `stream_chat` contracts.
- Typed request, response, chunk, and token usage models isolate future services from vendor payloads.
- `OpenAICompatibleProvider` maps non-streaming JSON and streaming SSE responses through `httpx`.
- `create_openai_compatible_provider()` converts application settings into an adapter only when a call path needs one.
- API keys use `SecretStr`, remain optional during health-only startup, and are required with a readable error at Provider initialization.
- Mock transports verify Provider behavior without real credentials or paid API calls.
- `ModelRegistry` loads strict JSON metadata, preserves configuration order, filters by provider, and resolves exact `(provider, model)` identities.
- Registry capability labels describe behavior implemented by this workspace. Streaming is enabled for the example entry; Tool Calling and JSON mode remain disabled until their scheduled work.
- Registry metadata is immutable. Unknown fields, blank names, negative prices, duplicate identities, unreadable files, and invalid JSON fail explicitly.

The Provider stream contract does not expose an HTTP endpoint yet. Chat routes,
service orchestration, persistence, and API-level SSE remain scheduled for M3.

The tracked Registry entry is example configuration. A Models API and frontend
selector remain deferred until the M3 application flow has services and routes.

## Security Boundaries

Secrets must not be committed.

Configuration examples may include empty variable names, but not real values. API keys should only be supplied through local `.env` files, environment variables, or a future approved secret mechanism.

Do not write secrets to:

- README
- docs
- tests
- fixtures
- screenshots
- logs
- frontend state
- database seed data

## Documentation Boundaries

- `docs-plan/` is the source of planning truth and execution sequencing.
- `docs/` is for formal project documentation that matches implemented or actively scoped behavior.
- `docs-local/` is for ignored local drafts, private review notes, and sensitive temporary material.

## Deferred Capabilities

The following are outside Plan 1:

- Tool execution
- Agent runtime loops
- RAG pipelines
- Embedding providers
- Memory systems
- MCP integrations
- Voice and vision
- Desktop packaging

These capabilities should be added only in their planned phases.
