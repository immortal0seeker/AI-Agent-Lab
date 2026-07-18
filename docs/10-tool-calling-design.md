# Tool Calling Design

## Current Scope

Plan 2 M1 establishes Tool contracts, discovery, validation, read-only security,
and persistence models. `P2-M2-S1` through `P2-M2-S3` add the first executable
built-in Tool, `read_file`, plus caller-controlled Registry initialization. No
Agent service, API, or Provider currently invokes it.

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

## Built-in read_file

`ReadFileTool` accepts one required string `path` and rejects unknown arguments.
It resolves only workspace-relative paths, requires a regular file, rejects
files over 1 MiB before reading, and checks the actual byte length again after
the read. A single read requests at most the byte limit plus one, preventing an
unbounded allocation if the file grows after `stat`. It accepts UTF-8 and UTF-8
BOM text, rejects NUL and non-UTF-8 content, and truncates returned text after
100,000 decoded characters.

Successful results place text in `ToolResult.content` and return a normalized
relative path, `utf-8` encoding, byte count, original/returned character counts,
and truncation state in metadata. Expected validation, security, file-size,
encoding, and filesystem failures return fixed safe failed ToolResults without
argument values, absolute paths, file contents, or raw exceptions.

`register_builtin_tools(registry, ...)` adds a configured `ReadFileTool` to a
caller-owned Registry. It creates no singleton and has no import-time or
application-startup side effect.

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

The implemented read_file path is:

```text
Caller-owned Registry -> ReadFileTool -> validation/security -> ToolResult
```

No current route or service invokes the Tool or creates AgentRun/ToolCall
records. `list_dir`, Provider integration, Agent Loop transitions, API access,
and frontend visualization are scheduled in later Plan 2 milestones.

## Verification and Security Boundary

Tests use Mock Tools, `tmp_path`, the tracked repository `README.md`, and
disposable SQLite databases. They do not read a real `.env`, user database,
credential, private key, or call a real Provider.

## Deferred Work

- Agent persistence service and transactions
- `list_dir` and optional `web_fetch` evaluation
- Provider tool calling
- Simple Agent Loop
- Agent APIs and frontend ToolCall visualization
- Plan 4 Trace, replay, and evaluation
