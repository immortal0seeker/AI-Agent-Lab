# Plan 2 M1 Tool Registry, Validation, and Security Design

## Scope

This design covers only `P2-M1-S4` through `P2-M1-S6`:

- an in-memory Tool Registry;
- Tool argument validation against JSON Schema;
- read-only workspace path security primitives;
- focused tests and the matching Plan 2 acceptance record.

AgentRun and ToolCall persistence, built-in tools, Provider tool calling, Agent
Loop execution, API routes, frontend work, RAG, Memory, MCP, and every later
Plan capability are outside this batch.

## Architecture

The new modules extend the transport-neutral Tool contract from S2-S3:

```text
Tool definition -> ToolRegistry -> OpenAI-compatible function schema
        |               |
        |               +-> exact-name lookup for a future executor
        |
        +-> JSON Schema validation -> validated arguments

Future read-only Tool -> path security policy -> safe workspace path
```

`app/tools/registry.py` owns Tool discovery and model-facing schema export.
`app/tools/validation.py` owns JSON Schema definition and argument validation.
`app/tools/security.py` owns pure path and limit checks. None of these modules
execute a Tool, access a Provider, persist state, or expose an API.

## Tool Registry

`ToolRegistry` stores Tool instances in registration order and indexes them by
their normalized exact name. It provides:

- `register_tool(tool)`: accept only `Tool` instances, reject duplicate names,
  and validate the Tool's parameter schema before making it discoverable;
- `get_tool(name)`: return the exact registered Tool or raise a typed not-found
  error;
- `list_tools()`: return a new list in registration order;
- `get_openai_tool_schemas()`: return deep-copied OpenAI-compatible function
  definitions containing `type`, `function.name`, `function.description`, and
  `function.parameters`.

Registry errors derive from `ToolError` so a future executor has one Tool
boundary to translate. Duplicate and missing Tool errors have dedicated types.
Failed registration is atomic: an invalid or duplicate Tool never changes the
registry. The registry does not support mutation through `unregister`, implicit
overwriting, startup discovery, or automatic builtin registration in this
batch.

## JSON Schema Validation

The backend adds `jsonschema` 4.x as a direct runtime dependency and uses the
Draft 2020-12 validator. A standards-based validator avoids maintaining an
incomplete local interpretation of JSON Schema and preserves the Tool's
parameter schema as the single source for both validation and Provider export.

`validate_tool_schema(schema)` checks the schema definition and raises
`ToolSchemaError` for an invalid schema. `validate_tool_arguments(tool,
arguments)`:

- requires a mapping and validates a copied plain dictionary;
- validates against the Tool's declared schema before future execution;
- collects deterministic validation issues rather than returning only the
  first failure;
- reports the instance path, validator code, and a safe human-readable message;
- never includes the rejected argument value in the exception text.

Unknown arguments are rejected only when a Tool schema declares
`additionalProperties: false`; the validator keeps normal JSON Schema semantics
instead of silently changing each Tool's contract. Validation does not execute
the Tool and does not create a ToolCall database record. Those responsibilities
belong to later steps.

## Read-only Path Security

`app/tools/security.py` defines `PROJECT_WORKSPACE_ROOT` from the repository
layout and exposes dependency-injectable pure checks so tests use only temporary
directories. The default policy supports future read-only tools while enforcing
these rules:

- accept workspace-relative paths only;
- reject blank paths, NUL bytes, absolute paths, drive-qualified paths, UNC
  paths, every raw or Windows-normalized `..` segment, alternate data streams,
  and trailing-dot/space aliases of sensitive names;
- resolve the candidate without requiring it to exist and verify that the
  resolved path remains below the configured workspace root;
- reject sensitive path components case-insensitively: `.env`, `.env.*`,
  `.ssh`, `.git`, and `docs-local`;
- reject common private-key names and extensions such as `id_rsa`, `id_dsa`,
  `id_ecdsa`, `id_ed25519`, `*.pem`, and `*.key`;
- provide pure file-size and directory-depth checks with conservative defaults
  for the later `read_file` and `list_dir` implementations.

The security module returns a resolved `Path` only after validation. It does not
open, enumerate, migrate, delete, or modify any file. The current batch never
reads a real `.env`, user database, credential store, SSH key, or browser
profile. Symlink escape is covered by resolved-path containment where the local
filesystem supports it; tests do not require privileged symlink creation on
Windows.

## Dependency and Export Boundaries

`jsonschema` is added to both `backend/pyproject.toml` and the root
`requirements.txt`, matching the repository's existing dependency mirrors. The
supported 4.x range will be selected from authoritative package metadata before
implementation and constrained below the next major version.

`app.tools` exports the public Registry, validation, and security contracts.
Internal helpers remain module-private. No API or service module needs to change
in this batch.

## Test Design

Implementation follows red-green-refactor cycles with three focused test
modules:

1. Registry tests cover registration, exact lookup, ordered listing, duplicate
   rejection, missing Tool errors, invalid Tool types, invalid schemas, atomic
   failure, OpenAI schema shape, and defensive copies.
2. Validation tests cover valid arguments, missing required fields, wrong
   types, unknown fields under `additionalProperties: false`, nested paths,
   multiple deterministic issues, invalid schemas, non-mapping arguments, and
   the absence of rejected values from errors.
3. Security tests use `tmp_path` only and cover valid relative paths, blank/NUL,
   absolute/drive/UNC paths, `..`, Windows trailing-dot/space aliases and
   alternate data streams, containment escapes, case-insensitive secret names,
   private keys, size limits, and depth limits.

After the focused tests pass, verification runs the complete backend pytest
suite, `pip check`, frontend typecheck, complete Vitest suite, and production
build. Documentation and scope checks include `git diff --check`, changed-file
inspection, secret-pattern review, and confirmation that no S7+ implementation
path was added.

## Acceptance Record

After fresh verification, the Plan 2 execution table will mark only S4-S6 and
the corresponding Batch 2 acceptance record complete. The record will capture
the implemented contracts, focused/full test evidence, mock or temporary-path
isolation, Codex self-review result, and the unchanged S7+ boundary.

## Deferred Work

- AgentRun and ToolCall persistence (`P2-M1-S7`)
- built-in `calculator`, `time`, `read_file`, and `list_dir` tools
- automatic builtin registration at application startup
- Tool execution timeout, result translation, and database persistence
- Provider tool calling and schema negotiation
- Agent Loop, APIs, and frontend Tool Call visualization
- every Plan 3 or later capability
