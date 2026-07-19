# Plan 2 v0.2.0 Basic Agent Release Candidate

## Release Status And Boundary

This document describes the Plan 2 release candidate reviewed through
`P2-M5-S7`. The final Codex review passed, all five Plan 3 bridge contracts were
revalidated, and backend/API/frontend release metadata is `0.2.0`. The latest
existing tag remains `v0.1.0`; `P2-M5-S8` stays open until the user creates the
`v0.2.0` release commit/tag and its target is verified. Nothing in this document
claims that the release tag already exists.

Plan 2 adds a safe, traceable read-only Tool Calling path and a bounded Simple
Agent loop on top of the Plan 1 Chat foundation. It does not add RAG, Embedding,
Memory, MCP, Shell/file-writing Tools, Planner, Human Approval, Browser Use, or
the later Agent Runtime.

## Implemented Surface

- Immutable Tool metadata, `ToolResult`, ordered caller-owned `ToolRegistry`,
  Draft 2020-12 object-root argument validation, and defensive Provider schemas.
- `read_file` and `list_dir` builtins with workspace-relative paths, bounded
  reads/traversal, sensitive-name filtering, safe failures, and no symlink or
  Windows junction traversal.
- Explicit `web_fetch` deferral: no module, schema, Registry entry, dependency,
  API, UI, or network implementation exists.
- Non-streaming Provider Tool definitions/calls and exact correlated Tool
  observations behind Provider-neutral contracts.
- A bounded `SimpleAgentService` with 1～10 Provider decisions, default 3,
  sequential Tool execution, finite per-Tool timeout, safe failure observations,
  bounded Provider context, and completed/failed AgentRun persistence.
- Plural synchronous Agent create/query routes under `/api/v1/agents/runs`.
- A responsive read-only Agent workspace with tools-capable model filtering,
  final answer/status/error, ToolCall arguments/results/latency, traceable IDs,
  and `?workspace=agent&run=<uuid>` restoration.

See [Tool Calling Design](10-tool-calling-design.md),
[Simple Agent Loop](11-simple-agent-loop.md), and [Agent API](12-agent-api.md)
for the detailed contracts.

## Current Flow

```text
Agent workspace
-> POST /api/v1/agents/runs
-> SimpleAgentService
-> tools-capable Provider decision
   -> final text
   -> or ordered read_file/list_dir calls
      -> validation + read-only security + finite timeout
      -> persisted ToolCall + correlated safe observation
      -> next Provider decision
-> committed completed or structured failed AgentRun
-> final answer and ToolCall audit cards
-> optional URL-backed AgentRun/ToolCall GET restoration
```

The service flushes and the API owns commit/rollback. Completed and structured
failed runs return HTTP 201 because both are persisted Agent resources. Preflight
configuration errors and transaction failures still use safe HTTP errors and
rollback.

## Local Startup And Model Requirement

Run Alembic before starting the backend, then start the frontend separately as
shown in the root [README](../README.md). SQLite remains the default and
long-term supported primary database.

The tracked `backend/app/providers/llm/models.json` entry intentionally remains
`supports_tools=false`. The Agent selector therefore shows no runnable model
until a local operator explicitly configures a tools-capable Registry entry and
matching Provider. Real credentials belong only in an untracked `backend/.env`
or process environment. They must never be written to Registry JSON, frontend
`VITE_*` variables, logs, screenshots, tests, or documentation.

## Security And Verification Model

Paths are workspace-relative. Absolute/drive/UNC paths, traversal, `.env*`,
credential names, private keys, browser/cloud/container credential directories,
alternate data streams, and followed symlink/junction targets are rejected.
Expected failures return fixed messages without raw arguments, absolute paths,
file content, credentials, Provider bodies, SQL, or exception text.

Automated verification uses Mock Providers/Tools, controlled temporary
workspaces, and newly created temporary SQLite databases. Browser verification
uses a local Vite server plus a temporary standard-library Mock API with fixed
synthetic UUIDs. It does not start the project backend, open a user database,
load `.env`, contact a real/paid Provider, or call a network Tool.

## Sanitized Agent ToolCall Demo

![Desktop Agent ToolCall workspace](assets/plan2/agent-tool-call-desktop.png)

Desktop-width release-candidate capture with a completed `read_file` ToolCall,
bounded result summary, latency, and traceable IDs.

![Mobile Agent ToolCall workspace](assets/plan2/agent-tool-call-mobile.png)

Mobile-width release-candidate capture of the same synthetic run. Exact
1280×900 and 390×844 acceptance viewports were separately checked for horizontal
overflow; the documentation canvases are taller only so the full audit card is
readable in one image.

## Current Limitations

- Tool Calling and Agent execution are synchronous and non-streaming.
- Tool Calls execute sequentially; there is no parallel execution or automatic
  retry.
- There is no AgentRun list, polling, user cancel/resume API, retry workflow, or
  persisted cancelled-run policy.
- ToolCall has no strict persisted step/sequence field. Runtime results preserve
  Provider order, while query order is deterministic but not a replay timeline.
- Intermediate assistant Tool Call/observation messages are not persisted in the
  Message table because it cannot preserve correlation fields.
- Agent Provider calls are not linked to `LLMCall` usage/cost rows.
- Provider observation compaction is character-based, not token-aware semantic
  summarization.
- The tracked example model is not enabled for Tools, and release verification
  does not prove live Provider Tool capability.
- `web_fetch` remains explicitly deferred with no executable surface.
- The supported package workflow remains an editable source install;
  `models.json` is not yet declared as future wheel/sdist package data.

## Release And Plan 3 Handoff

The full S7 Codex review is recorded in the
[Plan 2 v0.2.0 final review](reviews/2026-07-19-plan2-v0.2.0-final-review.md).
Its only runtime/release must-fix aligned the backend package, FastAPI OpenAPI,
frontend package, and lockfile versions with `0.2.0`; focused and full checks
then passed. S8 bridge evidence is ready, but this remains release-candidate
material until the user commits it, creates annotated tag `v0.2.0`, and the tag
target is verified. Plan 3 must not begin before that gate.
