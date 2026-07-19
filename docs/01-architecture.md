# Architecture

## Current Architecture Stage

This document describes the Plan 1 architecture delivered by `v0.1.0` and the
Plan 2 Tool Calling foundation built on top of it. The repository has
completed `P1-M1-S1` through `P1-M4-S8`, including the health
flow, database and Provider foundations, transactional Conversation and Chat
services, non-streaming and SSE Chat routes, Registry model selection,
conversation navigation, refresh recovery, successful-call usage persistence,
structured errors, request-linked logging, focused regression coverage,
recoverable frontend initialization states, clean-start documentation, release
materials, and the expanded final review. Plan 1 remains closed. Plan 2 has
completed `P2-M1-S1` through `P2-M4-S6`: Tool contracts, Registry, validation,
read-only path policy, AgentRun/ToolCall persistence, and the executable
`read_file` and `list_dir` builtins are available. The Provider contract now
accepts typed Tool definitions and normalizes non-streaming Tool Calls; an
independent adapter converts the Registry in stable order, and the
OpenAI-compatible adapter maps `tools` without leaking vendor payloads into
services. `web_fetch` remains deferred. A backend-only `SimpleAgentService`
now owns a bounded multi-step loop, observation backfill, per-Tool timeout,
structured failure results, observation compaction, and AgentRun/ToolCall
persistence. Validated plural Agent create/query routes expose that service. A
dedicated frontend Agent workspace consumes the synchronous API and renders
bounded ToolCall audit details; no network Tool is implemented at this stage.

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
│       ├── providers/
│       └── tools/
│           ├── base.py
│           ├── registry.py
│           ├── security.py
│           ├── validation.py
│           └── builtin/
│               ├── list_dir.py
│               └── read_file.py
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

Current backend layers:

| Layer | Responsibility |
|---|---|
| `api/` | HTTP routes and response shaping |
| `schemas/` | Pydantic request and response contracts |
| `services/` | Chat, conversation, Agent query, and application logic |
| `agents/` | Backend-only Simple Agent orchestration and Agent domain errors |
| `providers/` | LLM provider abstractions and adapters |
| `tools/` | Tool contracts, Registry, schema validation, and read-only policy |
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

The Plan 2 M1 migration adds:

- `agent_runs`
- `tool_calls`

All model IDs use UUID v4 values. Datetimes are stored as timezone-naive UTC
values because SQLite does not preserve timezone information consistently.
Deleting a conversation cascades to its messages and LLM calls. Deleting an
individual message preserves its LLM call records and sets `message_id` to
`NULL`.

`AgentRun` belongs to one Conversation and may reference the user Message that
started it. Deleting the Conversation cascades through its AgentRuns and
ToolCalls; deleting only that Message preserves the run and sets
`user_message_id` to `NULL`. `ToolCall` belongs to one AgentRun and repeats its
Conversation ID for direct lookup. A composite foreign key prevents that
Conversation identity from differing from its parent run.

Both records use UUID database identities. `ToolCall.tool_call_id` is a separate
string correlation identity and is unique within one AgentRun. Tool arguments
and results use JSON columns. Named status checks, non-negative latency checks,
timestamps, and lookup indexes establish persistence integrity without
introducing an Agent runtime state machine or persistence service.

Foreign-key columns used by conversation and message lookups are indexed.
SQLAlchemy metadata uses a stable naming convention for primary keys, foreign
keys, indexes, unique constraints, and check constraints so future Alembic
migrations can reference schema objects predictably on SQLite.

The create and read schemas feed thin HTTP routes and service-owned persistence
workflows. Update schemas remain deferred until an implemented behavior needs
them.

## Tool Calling Foundation

Plan 2 M1 defines an asynchronous `Tool` boundary and consistent `ToolResult`,
plus Provider/database-neutral ToolCall transport schemas. `ToolRegistry`
registers exact names in stable order, rejects duplicates, and exports defensive
OpenAI-compatible function schemas. JSON Schema Draft 2020-12 validation checks
tool schemas and arguments without echoing rejected values in errors.

The read-only security module resolves workspace-relative paths and rejects
absolute, drive, UNC, parent-traversal, sensitive, private-key, Windows alias,
and alternate-data-stream inputs. File-size and directory-depth limits remain
shared policy helpers.

`ReadFileTool` is the first consumer of this boundary. It validates one `path`
argument, resolves it below an injected workspace root, requires a regular file,
rejects files over 1 MiB before reading, rechecks the actual byte length, rejects
NUL and non-UTF-8 content, removes a UTF-8 BOM, and truncates returned text after
100,000 decoded characters. The read itself requests at most the byte limit plus
one, so a file growth race cannot cause an unbounded allocation. Successful
metadata contains only a normalized
workspace-relative path, encoding, byte/character counts, and truncation state.
Expected validation, security, size, encoding, and filesystem failures become
fixed safe failed `ToolResult` values without raw paths, content, or exception
text. File I/O runs through `asyncio.to_thread`.

`ListDirTool` accepts a workspace-relative `path` and an optional `max_depth`.
Depth 1 lists direct children, the default is 2, and the hard limit is 3. It
returns at most 500 entries by default, ordered by normalized relative path,
with name, `file`/`directory`/`symlink` type, and regular-file byte size. It
filters sensitive entries before metadata access or recursion, keeps ordinary
dotfiles such as `.gitignore`, reports but never follows discovered symlinks,
and returns fixed safe failures. Directory metadata work also runs through
`asyncio.to_thread`.

The implemented Tool data path is:

```text
Caller-owned ToolRegistry
-> register_builtin_tools()
-> ReadFileTool or ListDirTool
-> argument and workspace security validation
-> bounded UTF-8 read or directory traversal
-> ToolResult
```

The implemented non-streaming Provider definition/response path is:

```text
Caller-owned ToolRegistry
-> build_llm_tool_definitions()
-> ChatRequest.tools
-> OpenAI-compatible payload.tools
-> Provider message.tool_calls
-> normalized LLMToolCall objects
```

The Provider portion transports definitions and parses requests selected by a
model. Malformed argument JSON, non-object
arguments, invalid names/IDs, duplicate IDs, and unrequested Tool Calls become
fixed `ProviderResponseError` values without echoing the raw arguments.
Streaming Tool requests fail locally before HTTP because Tool Call delta
aggregation remains outside the completed non-streaming scope.

The implemented backend Agent path is:

```text
SimpleAgentRequest
-> tools-capable ModelRegistry gate
-> Conversation + user Message + AgentRun(running)
-> provider.chat(history + Tool definitions)
   -> direct text -> assistant Message + AgentRun(completed)
   -> ordered Tool Calls with another step available
      -> validation + timeout-bounded execution + ToolCall rows
      -> assistant Tool Call message + correlated Tool observations
      -> next provider.chat()
   -> Tool Calls on final allowed step -> AgentRun(failed), no execution
   -> Provider/blank terminal failure -> structured AgentRun(failed)
```

One Provider decision is one step; multiple Tool Calls in the same response run
sequentially in Provider order and still consume one step. `max_steps` defaults
to 3 and is limited to 10. The last allowed response cannot start Tool work.
Each Tool's finite timeout maps to the existing `timeout` ToolCall status, while
the failed observation lets a later Provider decision finish normally.
Intermediate Tool protocol messages remain in-process because the current
Message table cannot losslessly represent correlation fields. ToolCall rows
retain arguments, complete validated results, status, and timing; only the
Provider observation is compacted when it exceeds the configured character
bound. Runtime failure results remain committable because the service flushes
but does not commit.

The implemented HTTP boundary is:

```text
POST AgentRunCreate
-> AgentService input/content conversion
-> request-scoped SimpleAgentService
-> AgentRunExecutionRead + commit

GET AgentRun / ToolCalls
-> session-only AgentService
-> deterministic read schema
```

The POST response treats a structured failed AgentRun as a persistent HTTP 201
resource; preflight and transaction errors still use rollback and the unified
safe error envelope. The two GET routes never resolve Provider or Tool runtime
dependencies, so history remains readable without a configured Provider key.

`web_fetch` is intentionally absent from this architecture. A future
reassessment must define SSRF-safe address and redirect validation, DNS-
rebinding resistance, bounded streaming, content policy, text extraction,
safe errors, and mock acceptance coverage before exposing a network Tool.

The plural `/api/v1/agents/runs` POST and query routes and frontend Agent/ToolCall
visualization are implemented. Agent Provider calls are not yet linked to
`LLMCall`, and the existing ToolCall table
has no explicit sequence column; runtime results preserve Provider order while
queries use `created_at, id`, but a strict persisted step timeline belongs to
later AgentStep/Trace design. See [Tool Calling Design](10-tool-calling-design.md)
for the detailed boundary, [Simple Agent Loop](11-simple-agent-loop.md) for step
counting and failures, and [Agent API](12-agent-api.md) for the HTTP contract.

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

The frontend includes typed health, Models, Conversations, Messages, Chat, and
Agent API wrappers, an SSE parser, Zustand Chat state, page/component
boundaries, and a responsive Chat workspace. The store guards stale stream and
history callbacks, preserves partial output after Stop, and replaces temporary
messages with canonical backend data after a successful `done` event. It loads
Registry models and recent conversations independently, while
`?conversation=<uuid>` preserves the selected conversation across refreshes.

`App` uses small URL helpers to select the Chat or Agent workspace without
introducing a router or moving the existing Chat state. `AgentPage` independently
loads health and Registry models, filters to `supports_tools=true`, and owns the
synchronous create/restore flow. The controlled task form, result panel, and
ToolCall timeline/card components render loading, empty, no-model, completed,
structured failed, and transport-error states. Deterministic JSON plus bounded
result summaries keep the audit cards readable, while full
AgentRun, Conversation, Provider ToolCall, and database IDs remain visible.
`?workspace=agent&run=<uuid>` restores a persisted run through parallel AgentRun
and ToolCall reads. A request gate prevents a late POST response from mutating
state or URL after the Agent page unmounts.

`ChatPage` separates workspace initialization from ready-state message
rendering through `WorkspaceStatusPanel`:

```text
idle/loading -> initialization progress; composer and model selection disabled
error        -> one safe error plus a manual Retry action
Retry        -> initialize(valid conversation ID from the current URL)
ready        -> empty, conversation loading, streaming, completed, stopped, or Chat error
```

The Retry action reuses the existing Zustand initializer. It does not add an
automatic retry loop, delay, backoff, or new store state. Initialization errors
are rendered in the status panel rather than duplicated in the ready-state
error banner. Conversation-loading and Chat errors continue to use their
existing ready-state presentation.

Backend settings are loaded from `backend/.env` when backend commands run from
the backend directory. Vite loads `frontend/.env` for frontend commands. The
root `.env.example` is documentation-only in the current architecture and is
not automatically consumed by either application.

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

The current non-streaming flow uses server-owned history:

```text
Chat request with one new user turn
-> request-scoped SQLAlchemy Session
-> Registry model validation and Provider resolution
-> load or create Conversation
-> append user Message and load ordered history
-> BaseLLMProvider.chat()
-> append assistant Message and completed LLMCall
-> commit before the HTTP response is sent
```

Provider failures roll back all records created by that Chat request. On
success, normalized Provider usage, Registry-based estimated cost, and Provider
latency are stored on `LLMCall`. Missing usage leaves token and cost fields
`NULL`; an unknown input or output Registry price also leaves cost `NULL`.

The streaming flow owns a SQLAlchemy Session inside the response generator:

```text
POST /api/v1/chat/stream
-> validate model and resolve Provider
-> append the pending user turn and load ordered history
-> BaseLLMProvider.stream_chat()
-> emit SSE delta events while accumulating assistant text
-> append assistant Message and completed LLMCall
-> commit, then emit one SSE done event
```

If the Provider fails, the completion is empty, or the client cancels before
completion, the uncommitted turn is rolled back. The frontend retains stopped
partial text only in local state.

Streaming latency accumulates only the time spent awaiting Provider chunks, so
SSE consumer backpressure is not counted as model latency. The completed
`LLMCall` is committed before the terminal `done` event.

## Basic Errors And Request Logging

Every HTTP request receives a new server-generated UUID. The backend ignores
client-provided request IDs and returns its value in `X-Request-ID`. A pure ASGI
middleware keeps the same request context active until a streaming response is
fully consumed.

HTTP and SSE failures use the same inner error object:

```json
{
  "error": {
    "code": "provider_timeout",
    "message": "The model provider timed out",
    "request_id": "server-generated-uuid"
  }
}
```

Provider authentication, rate limit, timeout, bad request, server, response,
and unknown failures map to safe application errors. Database and unexpected
errors return fixed messages without exposing SQL, paths, stack text, upstream
response bodies, or credentials. SSE errors remain HTTP 200 after response
streaming has started and terminate with `event: error`.

Standard-library logs record request method/path/status/duration and model-call
provider/model/outcome/latency. They do not record request or response bodies,
complete messages, authorization headers, Provider error bodies, or SQL
parameters. This request-linked logging is a Plan 1 diagnostic foundation, not
the persistent Trace/Timeline system scheduled for Plan 4.

## Provider Principle

External AI capabilities should be provider-based. Plan 1 starts with LLM providers only. Later plans will add other provider families, but they should not be implemented during Plan 1 unless the active step explicitly requires them.

Plan 1 provider target:

- `BaseLLMProvider` defines vendor-neutral asynchronous `chat` and `stream_chat` contracts.
- Typed request, response, chunk, token usage, Tool definition, and Tool Call models isolate future services from vendor payloads.
- `build_llm_tool_definitions()` converts a caller-owned Tool Registry into defensive Provider definitions without executing tools.
- `OpenAICompatibleProvider` maps non-streaming JSON, non-streaming `tools`/`tool_calls`, and text-only streaming SSE responses through `httpx`.
- `create_openai_compatible_provider()` converts application settings into an adapter only when a call path needs one.
- API keys use `SecretStr`, remain optional during health-only startup, and are required with a readable error at Provider initialization.
- Mock transports verify Provider behavior without real credentials or paid API calls.
- `ModelRegistry` loads strict JSON metadata, preserves configuration order, filters by provider, and resolves exact `(provider, model)` identities.
- Registry capability labels describe behavior implemented for each configured model. Streaming is enabled for the example entry; Tool Calling stays disabled because the current batch proves the adapter protocol only and does not verify a real model or Agent path. JSON mode also remains disabled.
- Registry metadata is immutable. Unknown fields, blank names, negative prices, duplicate identities, unreadable files, and invalid JSON fail explicitly.

The Provider stream contract is consumed by `ChatService.stream_complete()` and
the protocol adapter at `POST /api/v1/chat/stream`. The service emits
protocol-neutral domain events; the route owns SSE framing and stream-scoped
Session cleanup. Streaming requests with Tool definitions are explicitly
unsupported and rejected before any Provider HTTP request.

The tracked Registry entry is example configuration. `GET /api/v1/models`
exposes non-secret Registry metadata in configuration order, and the frontend
uses exact `(provider, model)` identities. Conversation defaults remember the
last successfully used registered identity.

Conversation reads remain independent resources:

```text
GET /api/v1/conversations
GET /api/v1/conversations/{conversation_id}/messages
```

The list is ordered by recent successful activity. Messages retain deterministic
creation order. No composite workspace bootstrap endpoint, pagination, rename,
or delete behavior is introduced in M3.

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
