# Plan 2 M1 Tool Foundation Design

## Scope

This design covers only `P2-M1-S2` through `P2-M1-S3`:

- the `backend/app/tools/` package and common Tool execution contract;
- `Tool`, `ToolResult`, and `ToolError` base types;
- transport-neutral Tool Call request and response schemas;
- focused unit tests for metadata, result, and schema invariants.

Tool Registry, argument validation against JSON Schema, path security, built-in
tools, persistence, Provider tool calling, Agent Loop, API routes, and frontend
work are outside this batch.

## Architecture

The Tool foundation mirrors the existing LLM Provider boundary:

```text
Future Agent or Registry -> Tool.run(arguments) -> ToolResult
Future API or Agent schema -> ToolCallRequest / ToolCallResponse
```

`app/tools/base.py` owns executable Tool contracts and domain results.
`app/schemas/tool.py` owns Tool Call request and response serialization. Schemas
may depend on `ToolResult`; the Tool domain layer does not depend on API or ORM
modules.

## Tool Contract

`Tool` is an abstract class with validated constructor metadata:

- `name`: non-blank stable tool identifier with a 100-character limit;
- `description`: non-blank model-facing description;
- `parameters_schema`: copied JSON-like mapping, not yet validated as JSON Schema;
- `permission_level`: non-blank policy label whose concrete policy is defined in S6;
- `timeout_seconds`: positive execution limit;
- `async run(arguments) -> ToolResult`: the only execution method.

The constructor normalizes surrounding whitespace on text metadata, rejects
invalid metadata, and copies the parameter mapping so later caller mutation does
not silently change the Tool definition.

`ToolError` is the base runtime exception for Tool-boundary failures. This batch
does not add error subclasses or execution wrappers; later execution services
will translate expected failures into unsuccessful `ToolResult` values.

## ToolResult Contract

`ToolResult` is a strict Pydantic model with:

- `tool_name`;
- `success`;
- `content` with an empty-string default;
- optional structured `data`;
- optional `error`;
- isolated `metadata` with a default factory.

Successful results reject an error value. Failed results require a non-blank
error. Unknown top-level fields are rejected. This keeps failure handling
readable without introducing logging, persistence, or retry behavior.

## Tool Call Schemas

`ToolCallRequest` contains:

- a non-blank string `tool_call_id`, limited to 255 characters, that is neutral
  to Provider and database ID formats;
- a non-blank `tool_name` limited to 100 characters;
- an `arguments` mapping with an isolated empty default.

`ToolCallResponse` contains the same correlation ID and tool name, one of the
explicit Plan 2 statuses (`pending`, `running`, `success`, `failed`, `timeout`,
or `blocked`), and an optional `ToolResult`.

Pending and running responses do not contain a result. Terminal responses must
contain one. A successful status requires a successful result; other terminal
statuses require an unsuccessful result. The response tool name and result tool
name must match. Unknown top-level fields are rejected.

The correlation ID is not an ORM primary key. S7 may add a separate UUID-backed
record identity without changing this execution correlation contract.

## Test Design

Implementation follows red-green-refactor cycles with two focused test modules:

1. A concrete Mock Tool proves the async `run(arguments)` contract.
2. Tool construction rejects blank identifiers/descriptions/policy labels,
   non-mapping schemas, and non-positive timeouts.
3. Caller mutation cannot replace the copied Tool parameter mapping.
4. ToolResult validates success/error consistency and isolated defaults.
5. ToolCall schemas reject blank identifiers, invalid statuses, unknown
   top-level fields, and inconsistent response/result combinations.
6. Schema argument mappings use independent default values.
7. The complete backend test suite and `pip check` remain green.

Tests use only in-process Mock Tool objects. They do not read `.env`, access the
filesystem through a Tool, call a Provider, or execute external commands.

## Deferred Work

- Tool Registry (`P2-M1-S4`)
- JSON Schema argument validation (`P2-M1-S5`)
- read-only path security (`P2-M1-S6`)
- AgentRun and ToolCall persistence (`P2-M1-S7`)
- built-in tools, Provider tool calling, Agent Loop, API, and frontend work
