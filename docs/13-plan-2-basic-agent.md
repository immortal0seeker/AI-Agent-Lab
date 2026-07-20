# Plan 2 v0.2.0 Basic Agent Release And v0.2.1 Patch

## Release Status And Boundary

This document describes the completed Plan 2 release. The final Codex review
passed, all five Plan 3 bridge contracts were revalidated, and the user
published annotated tag `v0.2.0` from commit `0e3f3a6`, completing
`P2-M5-S8`. The current working tree prepares a `v0.2.1` audit-remediation
patch; its commit and tag do not yet exist, and the published `v0.2.0` tag must
not be moved.

Plan 2 adds a safe, traceable read-only Tool Calling path and a bounded Simple
Agent loop on top of the Plan 1 Chat foundation. It does not add RAG, Embedding,
Memory, MCP, Shell/file-writing Tools, Planner, Human Approval, Browser Use, or
the later Agent Runtime.

## Implemented Surface

- Immutable Tool metadata, `ToolResult`, ordered caller-owned `ToolRegistry`,
  standard-JSON/64 KiB argument bounds, Draft 2020-12 object-root validation,
  and defensive Provider schemas.
- `read_file` and `list_dir` builtins with workspace-relative paths, bounded
  reads/traversal, a 4096-character path limit, sensitive/private-key filtering,
  safe failures, and no user-supplied symlink or Windows junction traversal.
- Explicit `web_fetch` deferral: no module, schema, Registry entry, dependency,
  API, UI, or network implementation exists.
- Non-streaming Provider Tool definitions/calls and exact correlated Tool
  observations behind Provider-neutral contracts.
- A bounded `SimpleAgentService` with a 1～10 ToolCall execution budget (default
  3), atomic Provider batches, sequential read-only Tool execution, per-Tool and
  whole-run timeouts, safe failure observations, bounded Provider context, and
  completed/failed AgentRun persistence.
- Plural synchronous Agent create/query routes under `/api/v1/agents/runs`.
- A responsive read-only Agent workspace with tools-capable model filtering,
  final answer/status/error, bounded ToolCall arguments/results, strict sequence,
  latency, traceable IDs, URL restoration, and tab-scoped completed-run recovery.

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
       -> atomic budget + permission + validation before persistence
       -> finite timeout + sequenced ToolCall + correlated safe observation
      -> next Provider decision
-> committed completed or structured failed AgentRun
-> final answer and ToolCall audit cards
-> optional URL/session-backed AgentRun/ToolCall GET restoration
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
`supports_tools=false`. Copy `models.local.example.json` to the ignored
`models.local.json`, replace its synthetic model identifier, and point local
`MODEL_REGISTRY_PATH` at it to configure a Tool-capable model. Registry JSON
must not contain credentials. Real credentials belong only in an untracked
`backend/.env` or process environment and must never enter frontend `VITE_*`
variables, logs, screenshots, tests, or documentation. The whole-run deadline
is configured by `AGENT_RUN_TIMEOUT_SECONDS`, default `120`.

## Security And Verification Model

Paths are workspace-relative. Absolute/drive/UNC paths, traversal, `.env*`,
credential names, private-key names/content, browser/cloud/container credential
directories, alternate data streams, and every user-supplied symlink/junction/
reparse component are rejected. `list_dir` bounds every enumeration window.
Expected failures return fixed messages without raw arguments, absolute paths,
file content, credentials, Provider bodies, SQL, or exception text.

Automated verification uses Mock Providers/Tools, controlled temporary
workspaces, and newly created temporary SQLite databases. Browser verification
uses a local Vite server plus a temporary standard-library Mock API with fixed
synthetic UUIDs. It does not start the project backend, open a user database,
load `.env`, contact a real/paid Provider, or call a network Tool.

## Sanitized Agent ToolCall Demo

![Desktop Agent ToolCall workspace](assets/plan2/agent-tool-call-desktop.png)

Desktop-width release capture with a completed `read_file` ToolCall,
bounded result summary, latency, and traceable IDs.

![Mobile Agent ToolCall workspace](assets/plan2/agent-tool-call-mobile.png)

Mobile-width release capture of the same synthetic run. Exact
1280×900 and 390×844 acceptance viewports were separately checked for horizontal
overflow; the documentation canvases are taller only so the full audit card is
readable in one image.

## Current Limitations

- Tool Calling and Agent execution are synchronous and non-streaming.
- Tool Calls execute sequentially; there is no parallel execution or automatic
  retry.
- There is no AgentRun list, polling, user cancel/resume API, retry workflow, or
  persisted cancelled-run policy.
- ToolCall has strict persisted sequence, but there is no AgentStep/Trace or
  lossless Provider request/response replay timeline.
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
The user then created release commit `0e3f3a6`, annotated tag `v0.2.0`, and
pushed `main`, completing the original release gate. A post-release audit found
the Plan 2 boundary issues corrected by the current `v0.2.1` patch. After fresh
verification, the user may manually commit and tag `v0.2.1`; Codex does not
perform those Git mutations. The remaining limitations above are later-Plan or
explicitly accepted boundaries, not permission to implement Plan 3 early.
