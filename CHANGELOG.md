# Changelog

All notable changes to AI Agent Lab are documented in this file.

## [Unreleased]

## [0.2.1] - 2026-07-20

### Security And Reliability

- Enforced standard JSON and a 64 KiB UTF-8 limit for Tool arguments, plus a
  4096-character path schema limit for the built-in file Tools.
- Expanded private-key filename/container filtering, rejected recognized
  private-key content under arbitrary names, and prohibited user-supplied
  symlink or Windows reparse-point traversal.
- Bounded `list_dir` enumeration to `max_entries + 1` children per visited
  directory instead of materializing an unbounded directory.
- Enforced deny-by-default Agent dispatch: only `read_only` Tools execute, and
  unknown, invalid, oversized, or blocked call arguments are redacted before
  persistence.
- Defined `max_steps` as an atomic ToolCall execution budget, added a
  configurable whole-run timeout, and persisted one-based per-run unique
  `ToolCall.sequence_index` values through a backward-compatible migration.
- Added an optional `MODEL_REGISTRY_PATH` workflow with an ignored local file
  and a tracked secret-free Tool-capable example; the default Registry remains
  `supports_tools=false`.
- Made synchronous Agent results recoverable after leaving the page by storing
  only the run UUID in tab-scoped session storage; explicit run URLs still take
  priority and stale responses still cannot rewrite the Chat URL.
- Corrected ToolCall UI labels, summarized large argument payloads, and added
  mounted jsdom coverage for submit, restore, leave/reopen, structured failure,
  transport failure, and model-load failure flows.
- Synchronized backend, OpenAPI, frontend, lockfile, and documentation metadata
  to `0.2.1` without moving or recreating the published `v0.2.0` tag.

### Known Limitations

- Agent execution remains synchronous/non-streaming and sequential, with no run
  list, polling, cancel/resume/retry, or parallel Tool execution.
- Provider decisions are not strictly replayable and Agent calls are not linked
  to `LLMCall` usage/cost or later-Plan AgentStep/Trace records.
- Verification remains Mock-only; it does not prove live Provider Tool
  capability, and `web_fetch` remains deferred with no executable surface.

## [0.2.0] - 2026-07-19

### Added

- Added Provider-neutral assistant Tool Call and Tool observation messages with exact OpenAI-compatible serialization.
- Added a backend-only Simple Agent service for direct answers or a bounded non-streaming loop with 1～10 Provider decisions and a default of 3.
- Added per-Tool timeout enforcement, ordered multi-round observations, and bounded Provider observation JSON without truncating persisted ToolResult data.
- Added structured persisted Agent failures for maximum steps, Provider failures, invalid Provider results, and missing final text.
- Added AgentRun and ToolCall execution persistence with safe Tool failure observations, correlated results, timeout status, and timing metadata.
- Added validated Agent API schemas plus synchronous create, AgentRun query, and ToolCall query endpoints under `/api/v1/agents/runs`.
- Added persistent HTTP 201 responses for structured failed Agent runs and Provider-independent history queries with safe 404/error envelopes.
- Added a dedicated responsive Agent workspace with typed Agent API wrappers, tools-capable model filtering, and Chat/Agent sidebar navigation.
- Added bounded ToolCall cards and timeline states for arguments, status, latency, result summaries, safe errors, and traceable AgentRun/Conversation/Provider/database IDs.
- Added URL-backed AgentRun restoration plus mocked desktop/mobile acceptance for completed, failed, loading, no-model, transport-error, and reload states.
- Added regression coverage that locks `web_fetch` to its documented deferral boundary with no module, export, Registry schema, dependency, API, UI, or network implementation.
- Added sanitized desktop/mobile Agent ToolCall release-candidate screenshots and a consolidated pre-tag Plan 2 boundary document.

### Fixed

- Prevented `list_dir` from following Windows junctions and other reparse points outside the workspace, and corrected exact-limit truncation metadata.
- Blocked common credential files and directories such as `.npmrc`, `.netrc`, `.git-credentials`, `.aws`, `.kube`, and cloud credential JSON files from read-only tools.
- Made registered Tool definitions immutable and required Provider-exported parameter schemas to have a JSON-serializable object root.
- Enforced that an AgentRun's optional user Message belongs to the same Conversation through an additive Alembic migration.
- Rejected non-finite Tool timeouts, cross-round duplicate Tool Call IDs, and oversized escaped observation envelopes before they can break an Agent transaction.
- Prevented a late Agent response from updating state or rewriting the URL after the user leaves the Agent workspace.
- Rejected non-finite Tool argument values as non-standard JSON and extended the documented `.env*` path boundary to `.envrc` across shared policy and builtin Tools.
- Aligned backend package, FastAPI OpenAPI, frontend package, and lockfile release metadata with `0.2.0`.

### Known Limitations

- Plan 2 release verification uses Mock Providers and local synthetic browser data; it does not prove live Provider Tool capability, and the tracked example model remains `supports_tools=false`.
- Agent execution and Tool Calling are synchronous/non-streaming. There is no AgentRun list, polling, cancel/resume/retry, parallel Tool execution, or persisted cancelled-run policy.
- ToolCall has no strict persisted step sequence, and Agent Provider calls are not linked to `LLMCall` usage/cost rows.
- `web_fetch` remains explicitly deferred with no executable surface.

## [0.1.0] - 2026-07-13

### Added

- FastAPI and React/Vite project foundations with service-specific environment examples.
- SQLite/SQLAlchemy/Alembic persistence for conversations, messages, and successful LLM calls.
- Vendor-neutral LLM contracts, an OpenAI-compatible adapter, and a strict Model Registry.
- Non-streaming and SSE Chat with model selection, recent conversations, and refresh recovery.
- Successful-call token, estimated cost, and Provider latency persistence.
- Safe request IDs, classified HTTP/SSE errors, redacted request/model-call logs, and mocked regression coverage.
- Responsive Chat workspace states and sanitized desktop/mobile release screenshots.

### Security And Reliability

- Provider, database, validation, and unexpected failures return fixed readable responses without exposing credentials, SQL, upstream bodies, or complete messages.
- Failed and cancelled turns roll back instead of leaving partial persisted conversation state.
- Terminal SSE errors release the frontend response reader, and stale conversation-list refreshes cannot overwrite newer state.
- Release verification uses mocks and a fresh temporary database; it does not call a real Provider or modify the user's local database.

### Known Limitations

- Live DeepSeek/OpenRouter connectivity is configuration-supported but not exercised by release verification.
- Token, estimated cost, and latency are persisted on `LLMCall` but are not displayed in the frontend.
- Provider retries/fallback, persistent failed-call audit rows, and Plan 4 Trace are not implemented.
- SSE failures after response start use a terminal `event: error` frame on an HTTP 200 stream.
- `models.json` is not yet declared as wheel/sdist package data; the supported current workflow is an editable source install.
- Older ignored local SQLite databases can predate the current foreign-key indexes and are not automatically rebuilt.
- Conversation pagination/search/rename/delete and Markdown rendering are deferred.
