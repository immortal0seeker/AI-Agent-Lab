# Plan 1 Foundation Release

## Release Boundary

`v0.1.0` closes Plan 1 with a local-first, primarily single-user Web Chat
workspace. SQLite is the default and long-term supported primary database.
PostgreSQL remains optional compatibility work only if deployment or sustained
concurrency requirements materially change.

The release implements the project foundation, basic Chat, LLM Provider
abstraction, model selection, streaming, persisted history, usage metadata,
safe errors, and request-linked logs. Tool Calling, Agent Loop, RAG, Memory,
persistent Trace, MCP, Voice, Vision, and Desktop are outside this release.

## Implemented Workspace

- FastAPI backend and React/Vite/TypeScript frontend.
- SQLAlchemy models and Alembic migrations for conversations, messages, and
  successful LLM calls.
- Vendor-neutral asynchronous LLM contracts and an OpenAI-compatible adapter.
- Strict JSON Model Registry with exact provider/model identities.
- Non-streaming and SSE Chat with server-owned persisted history.
- Recent-conversation navigation, first-message titles, model restoration, and
  `?conversation=<uuid>` refresh recovery.
- Initialization loading/error/Retry states plus completed, streaming, stopped,
  and Chat error states.
- Successful-call token, estimated cost, and Provider latency persistence.
- Server-generated request IDs, classified safe errors, and redacted request
  and model-call logs.

## Architecture Map

The main flow is:

```text
React Chat workspace
-> FastAPI route and schema validation
-> Chat / Conversation service
-> LLM Provider adapter and SQLAlchemy session
-> committed messages + LLMCall
-> HTTP response or SSE terminal event
```

Routes remain thin, business transactions belong to services, and external
Provider details stay behind the Provider contract. See
[Architecture](01-architecture.md) for layer and transaction details and
[LLM Provider And Model Registry](03-llm-provider.md) for adapter, Registry,
usage, cost, latency, and error boundaries.

## API Surface

Plan 1 exposes these implemented routes:

```text
GET  /api/v1/health
POST /api/v1/conversations
GET  /api/v1/conversations
GET  /api/v1/conversations/{conversation_id}
GET  /api/v1/conversations/{conversation_id}/messages
GET  /api/v1/models
POST /api/v1/chat/completions
POST /api/v1/chat/stream
```

The Models, Conversations, and Messages reads are independent resources. Plan 1
does not add a composite bootstrap API, pagination, rename, delete, or search.

## Persistence And Transactions

A successful non-streaming or streaming turn atomically persists the user
message, assistant message, conversation metadata, and completed `LLMCall`.
Streaming commits before sending its terminal `done` event. Provider failure,
empty completion, database failure, or client cancellation rolls back the
request-owned turn; a stopped partial answer remains frontend-local only.

An older ignored local SQLite database can predate the current foreign-key
indexes. Release verification therefore uses a newly created temporary SQLite
database and never deletes, rebuilds, or silently migrates the user's local
database outside the normal explicit Alembic command.

## Errors, Logs, And Usage Metadata

Every HTTP request receives a server-generated UUID in `X-Request-ID`.
Structured HTTP failures and terminal SSE error events carry the same safe
request ID. Provider, database, validation, and unexpected failures use fixed
readable messages without exposing credentials, SQL, upstream response bodies,
or complete Chat content.

Successful calls store provider, model, input/output/total tokens, Registry-
based estimated cost, and Provider latency on `LLMCall`. Unknown usage or
pricing remains `NULL`; the workspace does not invent values. These metrics are
persisted for backend inspection but are not displayed in the current frontend.

## Frontend States

The frontend separates workspace initialization from ready-state Chat:

```text
idle/loading -> initialization status, disabled model/composer
error        -> one safe error and manual Retry
ready        -> empty, conversation loading, streaming, completed, stopped,
                or Chat error
```

The Retry action reuses the existing initializer and does not implement an
automatic retry/backoff loop. Stale initialization, history, conversation-list
refresh, and stream callbacks are guarded so late responses cannot overwrite
newer state. Terminal SSE errors cancel and release the response reader.

## Verification Model

The release is verified with backend unit/API/error tests, frontend TypeScript
and Vitest checks, a production build, fresh temporary Alembic migration checks,
Uvicorn/API smoke tests, and browser flows with intercepted API/SSE responses.
No release check calls a real or paid project Provider, and no real credential
is required.

The current evidence and review gates are recorded in the
[Plan 1 v0.1.0 final review](reviews/2026-07-13-plan1-v0.1.0-final-review.md).

Live DeepSeek/OpenRouter connectivity is configuration-supported through the
OpenAI-compatible adapter, but the `v0.1.0` release evidence does not claim that
a live upstream endpoint was exercised.

## Sanitized Demo

![Desktop Chat workspace](assets/plan1/chat-workspace-desktop.png)

Sanitized mock demonstration; no live Provider or real credential was used.

![Mobile Chat workspace](assets/plan1/chat-workspace-mobile.png)

Sanitized mock demonstration; no live Provider or real credential was used.

## Current Limitations

- The supported packaging workflow is an editable source install.
  `backend/pyproject.toml` does not yet declare `models.json` as wheel/sdist
  package data.
- Older ignored local SQLite databases can predate three current foreign-key
  indexes; they are not automatically rebuilt or deleted.
- An SSE failure after streaming starts remains an HTTP 200 response with a
  terminal `event: error` frame.
- Failed and cancelled calls roll back and do not persist a failed `LLMCall`
  audit row.
- Provider retries and fallback policy are not implemented.
- Token, estimated cost, and latency are not displayed in the frontend.
- Conversation pagination, search, rename, delete, and Markdown rendering are
  deferred.
- Real Provider connectivity is not part of release verification.

## Plan 2 Bridge

The next scope is `P2-M1-S1`, which verifies this tagged foundation before any
Tool Calling work begins. The bridge checks only that:

- the LLM Provider `chat` contract is stable enough to extend later;
- Conversation and Message identities can anchor later Agent records;
- non-streaming and streaming Chat coexist without blocking each other;
- request-linked logs identify provider, model, latency, outcome, and errors;
- a new developer can reproduce startup and verification from the README.

Passing these checks does not mean Tool Calling or an Agent Loop already exists.
