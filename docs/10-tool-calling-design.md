# Tool Calling Design

## Current Scope

Plan 2 M1 establishes Tool contracts, discovery, validation, read-only security,
and persistence models. It does not yet execute a Tool, expose an Agent API, or
call a Provider with Tool schemas.

## Tool Boundary

`Tool` owns normalized metadata, a JSON parameter schema, permission label,
timeout, and asynchronous `run(arguments) -> ToolResult`. `ToolResult` keeps
success, content, structured data, error, and metadata consistent. ToolCall
transport schemas keep Provider correlation IDs separate from ORM identities.

## Registry and Validation

`ToolRegistry` registers exact names, rejects duplicates, preserves order, and
exports defensive OpenAI-compatible function schemas. Draft 2020-12 validation
checks Tool schemas and arguments before future execution. Validation errors
contain safe paths and rules and never echo rejected argument values.

## Read-only Security

Paths are workspace-relative and resolved before use. Absolute, drive, UNC,
parent traversal, `.env`, sensitive directories, private keys, Windows path
aliases, and alternate data streams are rejected. File-size and directory-depth
limits are pure policy helpers. M1 does not read or enumerate files.

## Persistence

`AgentRun` records Conversation ownership, an optional user Message, simple
status, goal/final output/error, timing, and creation time. `ToolCall` uses a UUID
database ID plus a separate string `tool_call_id`, belongs to an AgentRun, keeps
direct Conversation lookup, stores JSON arguments/result, and records status and
timing. Composite and unique constraints prevent cross-Conversation ownership
and duplicate correlation IDs inside one run.

Deleting a Conversation removes its runs and calls. Deleting one user Message
keeps the audit record and nulls its link. Deleting an AgentRun removes its
ToolCalls.

## Status Values

AgentRun: `created`, `running`, `waiting_tool`, `completed`, `failed`,
`cancelled`.

ToolCall: `pending`, `running`, `success`, `failed`, `timeout`, `blocked`.

These are integrity values, not a full runtime state machine.

## Current Data Flow

M1 provides definitions and storage only:

```text
Future Agent service -> AgentRun -> validated ToolCall -> ToolResult
```

No current route or service creates these records. Built-in tools, Provider
integration, Agent Loop transitions, API access, and frontend visualization are
scheduled in later Plan 2 milestones.

## Verification and Security Boundary

Tests use Mock Tools, `tmp_path`, and disposable SQLite databases. They do not
read a real `.env`, user database, credential, or call a real Provider.

## Deferred Work

- Agent persistence service and transactions
- Built-in read-only tools
- Provider tool calling
- Simple Agent Loop
- Agent APIs and frontend ToolCall visualization
- Plan 4 Trace, replay, and evaluation
