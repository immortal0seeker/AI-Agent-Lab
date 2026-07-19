# Simple Agent Loop

## Scope

Plan 2 M3 provides a backend `SimpleAgentService` that connects the
Provider-neutral Tool protocol, caller-owned Tool Registry, read-only Tools,
Conversation persistence, and AgentRun/ToolCall audit records. It supports a
bounded non-streaming loop. Plan 2 M4 S1～S3 now expose it through synchronous
Agent create/query routes; no current frontend view invokes those routes.

This document describes `P2-M3-S1` through `P2-M3-S8`. M3 does not add RAG,
Embedding, Memory, MCP, Shell/file-writing Tools, a Planner, Human Approval, or
the Plan 5 Agent Runtime.

## Service Contract

`SimpleAgentRequest` contains:

| Field | Rule |
|---|---|
| `conversation_id` | Optional existing Conversation UUID |
| `provider` / `model` | Non-blank Registry identifiers |
| `content` | Non-blank user goal |
| `temperature` | `0..2` |
| `max_tokens` | Optional positive integer |
| `max_steps` | Strict integer `1..10`, default `3` |

Before writing any row, the service verifies that the model exists, explicitly
advertises `supports_tools=true`, and has a configured Provider. The tracked
example model remains `supports_tools=false`; tests inject a tools-capable Mock
Registry and do not prove live Provider support.

`SimpleAgentResult` always returns the Conversation, user Message, AgentRun,
executed ToolCall rows, Provider, and model. A successful result has an
assistant Message. A terminal runtime failure has `assistant_message=None` and
a failed AgentRun with a fixed safe error.

## Loop and Step Counting

One step is one Provider `chat()` decision, not one Tool Call:

```text
Conversation history + current user Message
-> AgentRun(running)
-> for each Provider decision up to max_steps
   -> final non-blank text
      -> assistant Message + AgentRun(completed)
   -> Tool Calls with another step available
      -> AgentRun(waiting_tool)
      -> validate and execute calls sequentially
      -> persist terminal ToolCalls
      -> append assistant Tool Call message and correlated observations
      -> AgentRun(running)
      -> next Provider decision
   -> Tool Calls on the last step
      -> AgentRun(failed), do not execute those calls
```

Multiple Tool Calls in one Provider response execute in Provider order but
consume only one step. With the default `max_steps=3`, the service can perform
two Tool rounds followed by final text. With `max_steps=1`, a Tool request is
not executed because no step remains for a final model decision.

Tool Call IDs must be unique across all executed rounds. A Provider response
that reuses an earlier ID terminates safely before the duplicate row or Tool
execution can occur.

## Provider-Neutral Messages

The Agent layer uses `ChatMessage` rather than OpenAI dictionaries:

- assistant Tool Call message: optional text plus normalized `LLMToolCall`
  objects;
- Tool observation: JSON text plus the matching `tool_call_id`.

The OpenAI-compatible adapter alone maps these messages to Chat Completions
`assistant.tool_calls` and `role=tool`. Ordinary Plan 1 Chat messages remain
`role/content` pairs, and streaming Tool Calls remain unsupported.

## Tool Execution and Timeout

Each attempted call creates a running ToolCall row before Registry lookup,
argument validation, or execution. After validation, `tool.run()` is wrapped
by the Tool's finite, positive `timeout_seconds` value.

| Outcome | ToolCall status | Safe error |
|---|---|---|
| successful ToolResult | `success` | none |
| unknown Tool / invalid arguments / failed or malformed result / exception | `failed` | stable Tool-specific failure |
| deadline exceeded | `timeout` | `Tool execution timed out` |

A failed or timed-out Tool becomes an observation; it does not immediately
fail the AgentRun. Remaining calls in the same response continue, and the next
Provider decision can explain the failure or choose another read-only Tool.

Timeout cancellation is cooperative. If a Tool has already delegated blocking
work to a thread, the coroutine deadline cannot forcibly stop that underlying
thread. Tools must therefore keep their own I/O bounded. M3 performs no
automatic retry: retrying future side-effecting Tools without the later
Runtime/Approval policy would be unsafe.

## Observation Bound

Full validated ToolResults are stored in `ToolCall.result_json`. Provider
observations use deterministic compact JSON and default to a 32,000-character
limit, configurable by the service with a minimum of 1,024 characters.

Results within the limit are unchanged. An oversized observation becomes a
valid JSON copy that:

- preserves `tool_name`, `success`, and a bounded error;
- truncates content to the greatest escaped JSON prefix that fits;
- sets `data` to `null`;
- replaces metadata with `observation_truncated=true` and the original
  serialized character count.

This does not mutate or truncate the persisted ToolResult. It is a character
bound, not token-aware semantic summarization. A single Provider response can
also contain multiple calls; M3 has no separate total Tool-call-count limit,
so the trusted Provider and registered read-only Tool set remain part of this
simple-loop boundary.

## Terminal Results and Transaction Ownership

Preflight configuration/request failures occur before persistence and retain
their existing domain exceptions. After AgentRun creation, expected runtime
terminations return a structured failed result:

| Condition | AgentRun error |
|---|---|
| Last allowed decision still requests Tool | `Agent reached the maximum number of steps` |
| Provider timeout | `Model request timed out` |
| Other Provider failure or invalid Provider result | `Model request failed` |
| Empty/blank terminal text | `Agent did not produce a final answer` |

Provider exception text, upstream bodies, arguments, absolute paths, and
credentials are not copied into these errors. Provider/task cancellation is
not swallowed. Database errors also propagate so callers can roll back a
failed SQLAlchemy transaction.

The service calls `flush()` but never `commit()`. A caller can commit both
completed and structured failed results. The M4 Agent API treats a failed
result as a normal persistence outcome, commits it through the request-scoped
database dependency, and maps AgentRun status/error to the API schema. Commit
or other database failure still escapes and triggers rollback.

## Persistence

M3 reuses the existing ORM and migrations:

- AgentRun: `running -> waiting_tool -> running`, then `completed` or `failed`.
- ToolCall: `running`, then `success`, `failed`, or `timeout`.
- Only the user and final successful assistant text enter `messages`.
- Intermediate assistant Tool Call and Tool observation messages remain
  in-process because the Message table cannot preserve correlation fields.
- `SimpleAgentResult.tool_calls` preserves runtime order. The database has no
  explicit sequence field and does not promise replay order by relationship.
- Agent Provider calls still have no Agent-linked `LLMCall`, so their
  usage/cost is not persisted.

No schema field, state, constraint, or Alembic revision was added in S7～S8.

## Verification and Security

Tests cover direct answers, existing history, two Tool rounds, multiple calls
per decision, final-step non-execution, cross-round ID reuse, safe Tool
failures, finite timeouts, cooperative cancellation, Provider failures and
invalid results, bounded observations including escaped JSON, and commit/reload
of completed and failed runs.

All Agent acceptance tests use Mock Providers, controlled Tools, temporary
SQLite databases, and temporary workspace files. They do not call a real or
paid Provider, access a network Tool, read a real `.env` or credential, or
touch the user's SQLite database.

## API Integration and Current Limitations

- The plural `/api/v1/agents/runs` create and query routes are available; no
  frontend Agent/ToolCall view exists yet.
- Tool Calling is non-streaming only.
- Tool Calls execute sequentially; no parallel execution or automatic retry.
- No user cancellation/resume API or persisted cancelled-run policy.
- No Agent-linked Provider usage/cost record or strict persisted step sequence.
- Observation compaction is character-based and lossy only for Provider context.
- `web_fetch` remains explicitly deferred with no runtime surface.

The next batch is `P2-M4-S4` through `P2-M4-S6`: add the frontend Agent API
wrapper and AgentRun/ToolCall presentation without changing the M3 loop
contract. See [Agent API](12-agent-api.md) for the implemented HTTP schemas,
transaction behavior, error mapping, and query boundaries.
