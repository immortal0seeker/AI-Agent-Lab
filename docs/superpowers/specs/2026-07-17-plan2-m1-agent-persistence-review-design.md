# Plan 2 M1 Agent Persistence and Review Design

## Scope

This design covers only `P2-M1-S7` through `P2-M1-S8`:

- SQLAlchemy models for `agent_runs` and `tool_calls`;
- one additive Alembic migration;
- focused model, relationship, constraint, and migration tests;
- the initial formal Tool Calling design document and M1 review record;
- correction of stale current-stage documentation now that Plan 2 M1 exists.

This batch does not add Pydantic Agent schemas, persistence services, Tool
execution, built-in tools, Provider tool calling, an Agent Loop, API routes,
frontend behavior, RAG, Memory, MCP, or any later-Plan capability.

## Architecture

The new persistence layer records future Agent execution without starting that
execution runtime:

```text
Conversation -> AgentRun -> ToolCall
      |              |
      +-> user Message (optional audit link)
```

ORM models own storage shape and relationships. Alembic owns schema creation.
No route, service, Provider, or Tool module writes these rows in this batch.
The existing SQLite-first SQLAlchemy conventions remain unchanged: UUID v4
identifiers, timezone-naive UTC datetimes, named constraints, indexed lookup
keys, and database-enforced foreign keys.

## AgentRun Model

`AgentRun` records one future Agent execution with:

- `id`: UUID v4 primary key;
- `conversation_id`: required indexed UUID linked to `conversations.id` with
  `ON DELETE CASCADE`;
- `user_message_id`: optional indexed UUID linked to `messages.id` with
  `ON DELETE SET NULL` so deleting one message preserves the run audit row;
- `status`: required string defaulting to `created`;
- `goal`: required text;
- optional `final_answer` and `error_message` text;
- optional `started_at`, `ended_at`, and `latency_ms`;
- `created_at`: required UTC creation timestamp.

Allowed status values are `created`, `running`, `waiting_tool`, `completed`,
`failed`, and `cancelled`. A database check constraint rejects other values.
Another check rejects negative non-null latency. This is an integrity contract,
not a state machine; transition rules remain deferred to the Agent Loop work.

An `AgentRun` belongs to one Conversation, may reference one user Message, and
owns a collection of ToolCall rows. The pair `(id, conversation_id)`
has a named unique constraint so ToolCall can use it as a composite parent key.

## ToolCall Model

`ToolCall` separates storage identity from execution correlation:

- `id`: UUID v4 database primary key;
- `tool_call_id`: required string correlation ID, limited to 255 characters;
- `agent_run_id` and `conversation_id`: required indexed UUID values forming a
  composite foreign key to `agent_runs(id, conversation_id)` with
  `ON DELETE CASCADE`;
- `tool_name`: required string limited to 100 characters;
- `arguments_json`: required JSON object with an isolated dictionary default;
- `result_json`: optional JSON object;
- `status`: required string defaulting to `pending`;
- optional `error_message`, `started_at`, `ended_at`, and `latency_ms`;
- `created_at`: required UTC creation timestamp.

The composite foreign key prevents a ToolCall from claiming a Conversation that
differs from its AgentRun while retaining the direct `conversation_id` lookup
column required by the Plan 2 database design. `(agent_run_id, tool_call_id)` is
unique, allowing different runs to reuse a Provider correlation ID without
allowing duplicates inside one run.

Allowed ToolCall status values are `pending`, `running`, `success`, `failed`,
`timeout`, and `blocked`, matching the existing ToolCall transport schema. A
database check rejects other values, and a second check rejects negative
non-null latency.

## Relationship and Delete Rules

- Deleting a Conversation deletes its AgentRun rows and, through the composite
  AgentRun foreign key, their ToolCall rows.
- Deleting an AgentRun deletes its ToolCall rows.
- Deleting an individual user Message sets `AgentRun.user_message_id` to null
  and preserves the run and ToolCall audit records.
- ToolCall ownership is through AgentRun. It does not define a second mutable
  Conversation ORM ownership relationship, avoiding overlapping cascade paths.
- The future persistence service must create ToolCall rows through their
  AgentRun relationship; no such service is added in this batch.

## Migration

Revision `20260717_0002` follows `20260712_0001` and creates `agent_runs` before
`tool_calls`. It includes every ORM column, check constraint, unique constraint,
foreign-key action, and foreign-key lookup index. Downgrade removes ToolCall
indexes/table first and then AgentRun indexes/table, returning the database to
the Plan 1 schema.

Migration verification uses only a new temporary SQLite database. It runs
upgrade to head, current/head checks, Alembic schema comparison, downgrade to
the previous revision, re-upgrade, and downgrade to base where appropriate.
The ignored `backend/ai_agent_lab.db` is never read, migrated, deleted, or
rebuilt.

## Test Design

Implementation follows red-green-refactor cycles with focused tests for:

1. UUID IDs, default statuses, UTC timestamps, JSON round-trips, and ORM
   relationships.
2. Isolated default argument dictionaries.
3. Conversation deletion cascading to AgentRun and ToolCall.
4. AgentRun deletion cascading to ToolCall.
5. Message deletion nulling `user_message_id` while preserving audit rows.
6. Invalid AgentRun/ToolCall statuses and negative latency being rejected.
7. Duplicate `(agent_run_id, tool_call_id)` and mismatched Conversation IDs
   being rejected.
8. Alembic upgrade creating exact columns, constraints, indexes, and delete
   actions; downgrade returning to the previous schema.
9. Existing Plan 1 database, Chat, Provider, and frontend tests remaining green.

All database tests use `tmp_path` or a new system temporary SQLite file. Tests
do not read a real `.env`, user database, credential, or Provider.

## M1 Documentation and Review

`docs/10-tool-calling-design.md` becomes the formal description of the
implemented M1 foundation:

- Tool/ToolResult contracts and transport schemas;
- Registry discovery and OpenAI-compatible schema export;
- Draft 2020-12 argument validation and safe errors;
- read-only path and resource security policy;
- AgentRun and ToolCall persistence contracts;
- current limitations and the explicit boundary before executable tools.

The current-stage sections in `README.md`, `README_CN.md`,
`docs/00-project-overview.md`, and `docs/01-architecture.md` are updated because
their current claim that no Plan 2 capability exists is already false. The
released `v0.1.0` history and its CHANGELOG entry remain unchanged.

After fresh verification, the Plan 2 execution table marks only Batch 3 and
S7-S8 complete, records M1 acceptance evidence, and names `P2-M2-S1～S3` as the
next batch without implementing it.

Codex performs the required M1 self-review. The repository instruction that
external Claude Code review requires an explicit user request remains in force,
so this batch records that Claude Code was not run and recommends revisiting it
at the user-selected review checkpoint.

## Deferred Work

- AgentRun and ToolCall create/read Pydantic schemas
- persistence services and transaction workflows
- built-in `read_file`, `list_dir`, or other executable tools
- Provider tool-call request/response support
- Simple Agent Loop and state transitions
- Agent APIs and frontend Tool Call visualization
- Trace/Event persistence, replay, evaluation, and every Plan 3+ capability
