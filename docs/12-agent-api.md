# Agent API

## Scope

Plan 2 M4 S1～S3 exposes the existing non-streaming `SimpleAgentService`
through a synchronous FastAPI surface:

```text
POST /api/v1/agents/runs
GET  /api/v1/agents/runs/{run_id}
GET  /api/v1/agents/runs/{run_id}/tool-calls
```

The resource name is always plural `agents`; there is no singular
`/api/v1/agent/runs` alias. These endpoints add no new Agent state, database
field, migration, Tool, or Provider protocol.

## Create a Run

`POST /api/v1/agents/runs` validates this request:

```json
{
  "conversation_id": null,
  "provider": "openai_compatible",
  "model": "tools-enabled-model",
  "input": "Read README.md and summarize the workspace",
  "temperature": 0.7,
  "max_tokens": null,
  "max_steps": 3
}
```

| Field | Rule |
|---|---|
| `conversation_id` | Optional existing Conversation UUID; omission creates one |
| `provider` | Non-blank Registry identifier, at most 100 characters |
| `model` | Non-blank Registry identifier, at most 255 characters |
| `input` | Non-blank Agent goal |
| `temperature` | `0..2`, default `0.7` |
| `max_tokens` | Optional positive integer |
| `max_steps` | Strict integer `1..10`, default `3` |

Unknown fields are rejected. `content` is not accepted as an alias for
`input`. Before creating any row, the Agent verifies that the Registry model
exists, advertises `supports_tools=true`, and has a configured Provider.

The endpoint is synchronous: it waits for a final completed or failed
AgentRun. A successful response is HTTP 201:

```json
{
  "id": "00000000-0000-0000-0000-000000000101",
  "conversation_id": "00000000-0000-0000-0000-000000000102",
  "user_message_id": "00000000-0000-0000-0000-000000000103",
  "status": "completed",
  "goal": "Read README.md and summarize the workspace",
  "final_answer": "The workspace contains a FastAPI backend and React frontend.",
  "error": null,
  "started_at": "2026-07-19T12:00:00",
  "ended_at": "2026-07-19T12:00:01",
  "latency_ms": 1000,
  "created_at": "2026-07-19T12:00:00",
  "tool_calls": []
}
```

The POST response includes every ToolCall actually executed during the run in
runtime order. A ToolCall exposes:

- database `id` and Provider `tool_call_id`;
- `agent_run_id` and `conversation_id`;
- `tool_name` and validated `arguments`;
- complete persisted `result` or `null` for a non-terminal historical row;
- `status`, safe `error`, timestamps, and `latency_ms`.

The current API maps ORM `arguments_json`, `result_json`, and `error_message`
to the public names `arguments`, `result`, and `error`.

## Failed Runs and Transactions

Once an AgentRun has been created, expected runtime failures are persistent
business outcomes rather than failed HTTP transport. Provider timeout/failure,
an invalid Provider result, blank terminal text, or exhausting `max_steps`
therefore returns HTTP 201 with:

```json
{
  "status": "failed",
  "final_answer": null,
  "error": "Model request timed out"
}
```

The complete response still contains IDs, timing, and any ToolCalls that had
already reached terminal state. The request-scoped database dependency commits
both completed and structured failed results. Schema, model capability,
Provider availability, Conversation existence, cancellation, and database
errors that escape before a normal result use the request rollback path.
Commit failure cannot return a false 201.

Runtime errors are fixed and safe. Provider exception text, credentials,
upstream bodies, SQL diagnostics, stack traces, and absolute local paths are
not copied into the response.

## Query a Run

`GET /api/v1/agents/runs/{run_id}` returns the AgentRun fields without the
`tool_calls` collection. It does not construct the Provider or Tool execution
dependencies, so history remains readable when no Provider API key is locally
configured.

`GET /api/v1/agents/runs/{run_id}/tool-calls` returns the run's ToolCalls.
An existing run with no calls returns `200 []`. The service checks that the
parent AgentRun exists first; an unknown run returns 404 rather than an
ambiguous empty list.

Query results use `created_at ASC, id ASC` for deterministic display. The
database does not yet have a strict step/sequence column, so this ordering is
not a lossless persisted replay timeline. POST preserves the in-memory runtime
order supplied by `SimpleAgentResult`.

## HTTP Errors

All errors use the existing request-ID envelope.

| Condition | HTTP | Code |
|---|---:|---|
| Request field or UUID is invalid | 422 | `validation_error` |
| Registry model is missing | 400 | `model_not_found` |
| Registry model does not support Tools | 400 | `model_tools_unsupported` |
| Provider is unavailable | 503 | `provider_unavailable` |
| Conversation is missing | 404 | `conversation_not_found` |
| AgentRun is missing | 404 | `agent_run_not_found` |
| Database operation fails | 503 | `database_error` |

## Tool and Provider Boundary

The production dependency creates a fresh Tool Registry per POST and registers
only `read_file` and `list_dir`. Both remain read-only, workspace-relative,
bounded, sensitive-name aware, and unable to follow discovered symlink,
junction, or reparse-point content outside the trusted workspace. Tool results
are intentionally returned for the user-visible Agent audit trail; sensitive
paths remain blocked by the Tool security layer.

The tracked example model still declares `supports_tools=false`. Automated
acceptance uses a tools-capable Mock Registry, Mock Providers, temporary SQLite,
and temporary workspace files. It proves the local API contract, not live or
paid Provider connectivity.

## Current Limitations

- No frontend Agent API wrapper, ToolCall card/timeline, or Agent page exists;
  these belong to `P2-M4-S4～S6`.
- Tool Calling is non-streaming and ToolCalls execute sequentially.
- No automatic retry, user cancel/resume API, or persisted cancelled-run policy.
- Agent Provider calls are not linked to `LLMCall` usage/cost rows.
- ToolCall has no strict persisted step sequence.
- `web_fetch` remains deferred with no runtime or API surface.
- No RAG, Embedding, Memory, MCP, Shell, file-writing, or file-deletion Tool is
  part of Plan 2.

See [Simple Agent Loop](11-simple-agent-loop.md) and
[Tool Calling Design](10-tool-calling-design.md) for the underlying runtime and
security contracts.
