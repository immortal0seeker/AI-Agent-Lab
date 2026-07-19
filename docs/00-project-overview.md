# AI Agent Lab Project Overview

## Positioning

AI Agent Lab is a staged AI Engineering Workspace for developers and AI application engineers. It is designed as a long-running learning and reference implementation project, not as a set of isolated demos.

The project starts with a small web chat foundation and gradually expands into tool calling, RAG, traceability, memory, agent runtime, MCP, voice, vision, and desktop capabilities.

The workspace is local-first and primarily single-user. SQLite is its default and long-term supported primary database. PostgreSQL compatibility may be retained where inexpensive, but migration to PostgreSQL is not a roadmap requirement and should be reconsidered only if deployment or concurrency requirements change.

## Goal

The goal is to build a usable, observable, testable, and extensible AI engineering workspace. Each plan should leave the repository in a working state that can be reviewed, tested, documented, and extended by the next plan.

The project emphasizes:

- Clear module boundaries
- Provider-based external integrations
- Testable services
- Observable model and agent behavior
- Reproducible evaluation and verification
- Documentation that matches implemented behavior
- Local-first operation with low setup and maintenance cost

## Plan Roadmap

| Plan | Scope | Target |
|---|---|---|
| Plan 1 | Project foundation, basic chat, LLM providers | `v0.1.0` |
| Plan 2 | Tool Calling and simple Agent Loop | `v0.2.0` |
| Plan 3 | Knowledge Base, document ingestion, Naive RAG | `v0.3.0` |
| Plan 4 | Trace, Advanced RAG, rerank, evaluation | `v0.4.0` |
| Plan 5 | Memory, Context Engine, Agent Runtime, Human Approval | `v0.5.0` |
| Plan 6 | MCP, Voice, Vision, Desktop | `v0.6.0` |

## Current Stage

Current release: Plan 1 is complete as the `v0.1.0` foundation release.
Current development stage: the first two Plan 2 M3 batches are complete through
`P2-M3-S6`.

The repository has completed `P1-M1-S1` through `P1-M4-S8`. Milestone 1 assembled the engineering foundation, Milestone 2 added the database and Provider foundations, Milestone 3 completed the persisted Chat loop, and Milestone 4 added:

- Repository structure
- Root documentation
- Backend and frontend directories
- FastAPI health check
- Backend and frontend environment examples
- Frontend API client
- Frontend health status display with loading, healthy, and error states
- Local environment examples
- Clear documentation boundaries
- Configurable SQLite connection and SQLAlchemy session
- Alembic-managed initial migration
- UUID-based Conversation, Message, and LLMCall models
- Pydantic create and read schemas for the three models
- Vendor-neutral asynchronous LLM Provider contracts
- OpenAI-compatible non-streaming and SSE streaming adapter
- Environment-backed Provider initialization with masked API keys
- Mock HTTP coverage for response, usage, stream, and error handling
- Strict JSON Model Registry with immutable capability metadata
- Provider and Registry documentation
- Transactional Conversation Service
- Non-streaming Chat Service with server-owned history
- Conversation and Chat API routes
- Mock Provider API and rollback coverage
- Transactional SSE Chat with `delta`, `done`, and readable `error` events
- Successful-completion-only stream persistence and cancellation rollback
- Typed frontend SSE parsing and Zustand Chat state
- Responsive Chat workspace with empty, streaming, success, stopped, and error states
- Mocked browser verification on desktop and mobile
- Read-only Models, recent Conversations, and ordered Messages APIs
- Automatic first-message titles and last-successful model metadata
- Registry-backed frontend model selection
- Recent conversation navigation and `?conversation=<uuid>` refresh recovery
- Stale initialization/history/conversation-refresh/stream-response suppression
  and complete frontend regression coverage
- Successful non-streaming and streaming `LLMCall` token/cost/latency persistence
- Decimal Registry pricing with explicit `null` handling for unknown usage or prices
- Classified Provider errors without upstream body or credential leakage
- Unified HTTP/SSE error envelopes with server-generated request IDs
- Safe request and model-call logs containing request ID, model, outcome, and latency
- Focused health, Provider stream, classified Chat rollback, Conversation, and safe-error regression coverage
- Distinct frontend workspace initialization loading and error states
- Manual Retry recovery after initialization failure without an automatic retry loop
- Clean-start, service-specific environment, migration, and verification documentation
- Sanitized desktop/mobile release demonstrations, a changelog, current limitations, and final review evidence

Plan 2 M1 (`P2-M1-S1` through `P2-M1-S8`) verified the tagged handoff and added
Tool contracts, ToolCall transport schemas, Registry and argument validation,
read-only path policy, and AgentRun/ToolCall persistence models. These are
foundation contracts. `P2-M2-S1` through `P2-M2-S6` add two executable
read-only builtins. `read_file` provides bounded workspace-relative UTF-8
reads. `list_dir` provides deterministic recursive listings with default depth
2, hard depth 3, a default 500-entry bound, structured name/type/size data,
sensitive-name filtering, and non-followed discovered symlinks. Both return
safe failure results and register into a caller-controlled Registry.
`P2-M2-S7` evaluated and explicitly deferred `web_fetch`; no network Tool,
schema, helper, dependency, API, or UI was added. `P2-M3-S1` through
`P2-M3-S3` add typed non-streaming Provider Tool definitions and Tool Calls, a
defensive Registry-to-Provider schema adapter, safe OpenAI-compatible `tools`
serialization, and normalized single/multiple Tool Call parsing. Streaming
Tool Calls are explicitly rejected before HTTP, and the tracked example model
remains `supports_tools=false`. At the S1～S3 transport boundary, Tool
execution, the Agent Loop, persistence services, Agent APIs, and frontend
Agent/ToolCall views were still deferred.

`P2-M3-S4` through `P2-M3-S6` add a backend-only `SimpleAgentService`. It
validates an explicitly tools-capable model, creates or reuses a Conversation,
persists the user Message and AgentRun, and either completes from one Provider
text response or executes one ordered Tool round. Tool results are correlated
back into Provider-neutral observation messages, a second and final Provider
call supplies the answer, and each attempted Tool Call receives a terminal
audit row. Agent API/UI, general max-step/timeout/retry/failure policy, strict
persisted parallel-call ordering, and Agent-linked LLM usage records remain
deferred.

The next batch is `P2-M3-S7` through `P2-M3-S8`. See the
[Tool Calling design](10-tool-calling-design.md),
[Plan 1 foundation release](02-plan-1-foundation.md), and root
[changelog](../CHANGELOG.md) for the current boundaries and limitations.

## Plan 1 Scope

Plan 1 should produce a basic Web ChatGPT-style workspace foundation:

- FastAPI backend
- React + TypeScript frontend
- Health check endpoint
- SQLite-backed conversation storage
- LLM Provider abstraction
- OpenAI-compatible provider support
- Chat API
- Streaming chat
- Conversation history
- Basic usage, cost, latency, logging, and error handling

## Plan 1 Non-Goals

Plan 1 must not implement:

- Tool Calling
- Agent Loop
- RAG
- Embedding
- Memory
- MCP
- Voice
- Vision
- Desktop
- Multi-agent workflows

If a later-plan capability appears necessary, record it as a bridge item instead of implementing it early.

## Documentation Policy

The repository uses three documentation areas:

- `docs-plan/`: tracked source planning documents and execution step tables.
- `docs/`: tracked formal project documentation and sanitized verification assets.
- `docs-local/`: ignored local drafts, private notes, temporary reviews, sensitive screenshots, and debugging notes.

Only sanitized, durable documentation should move from `docs-local/` into tracked project documents.
