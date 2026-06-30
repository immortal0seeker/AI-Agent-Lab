# Architecture

## Current Architecture Stage

This document describes the Plan 1 architecture target. The repository is currently at the beginning of Plan 1 Milestone 1, so some modules are documented as intended structure and will be implemented in later Plan 1 batches.

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

The first backend endpoint will be:

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

Streaming and persistence are part of Plan 1, but they should be implemented in later Plan 1 batches after the skeleton and provider layer exist.

## Provider Principle

External AI capabilities should be provider-based. Plan 1 starts with LLM providers only. Later plans will add other provider families, but they should not be implemented during Plan 1 unless the active step explicitly requires them.

Plan 1 provider target:

- Define a stable LLM provider interface.
- Implement an OpenAI-compatible adapter.
- Support configured providers such as DeepSeek or OpenRouter without hard-coding secrets.

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
