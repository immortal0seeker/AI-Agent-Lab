# AI Agent Lab

[English](README.md) | [中文](README_CN.md)

AI Agent Lab is a staged AI Engineering Workspace for learning and building the core systems behind modern AI applications. It starts with a stable FastAPI + React foundation and grows through chat, provider abstraction, tool calling, RAG, traceability, memory, agent runtime, MCP, voice, vision, and desktop workflows.

This repository is not a collection of disconnected demos. The goal is to build a usable, observable, testable, and extensible AI engineering workspace one plan at a time.

## Current Stage

Current plan: Plan 1, target `v0.1.0`.

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

Completed scope: `P1-M1-S1` through `P1-M2-S3`.

Next scope: `P1-M2-S4` through `P1-M2-S6`.

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

The backend and frontend are scaffolded in stages. Milestone 1 now supports
starting both apps locally and verifying the backend health endpoint from the
frontend home page.

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

```bash
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL printed by `npm run dev`. The home page shows the configured
`VITE_API_BASE_URL` and one of these health states:

- `Checking health...` while the frontend is calling the backend.
- `Backend healthy` when `GET /api/v1/health` returns successfully.
- `Backend error` when the backend is not reachable or returns an error status.

Frontend checks:

```bash
npm run typecheck
npm run test
npm run build
```

Batch 4 commit note: the user creates the actual Git commit manually after
reviewing the verified diff. Suggested commit message:

```text
feat(db): add sqlite models migrations and schemas
```

For now, use the plan documents as the source of truth:

- `docs-plan/00-ALL PLAN/01-PLAN-1 (V1.0).md`
- `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

## Roadmap

- Plan 1: Project foundation + Basic Chat + LLM Providers
- Plan 2: Tool Calling + Simple Agent Loop
- Plan 3: Knowledge Base + Document Ingestion + Naive RAG
- Plan 4: Trace + Advanced RAG + Rerank + Evaluation
- Plan 5: Memory + Context Engine + Agent Runtime + Human Approval
- Plan 6: MCP + Voice + Vision + Desktop
