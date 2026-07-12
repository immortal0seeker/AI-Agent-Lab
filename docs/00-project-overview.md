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

Current stage: Plan 1, Milestone 3 in progress; its backend streaming and first frontend Chat flow are complete.

The repository has completed `P1-M1-S1` through `P1-M3-S6`. Milestone 1 assembled the engineering foundation, Milestone 2 added the database and Provider foundations, and M3 currently adds:

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

The next scope is `P1-M3-S7` through `P1-M3-S9`, which adds model selection, conversation navigation, refresh recovery, and M3 test completion.

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
