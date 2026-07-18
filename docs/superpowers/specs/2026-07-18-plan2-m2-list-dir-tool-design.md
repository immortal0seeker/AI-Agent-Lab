# Plan 2 M2 list_dir Tool Design

**Date:** 2026-07-18

**Scope:** `P2-M2-S4` through `P2-M2-S6` only.

## Goal

Add a safe, bounded, recursively structured `list_dir` Tool that lists files
and directories inside the configured workspace, hides sensitive entries,
returns stable text and structured results, and is registered beside
`read_file` in the caller-owned Tool Registry.

## Non-goals

- Do not implement or decide `P2-M2-S7` `web_fetch`.
- Do not add Provider tool calling, an Agent Loop, Agent services or APIs, or
  frontend Agent views.
- Do not add database records or migrations.
- Do not recursively follow symbolic links discovered during directory
  traversal or read file contents.
- Do not add Shell, file-writing, file-deleting, RAG, Embedding, Memory, MCP,
  Voice, Vision, Desktop, or later-plan capabilities.
- Do not access the user's real `.env`, credentials, private keys, or local
  database.

## Tool Contract

`ListDirTool` is an asynchronous, read-only Tool named `list_dir`.

Its JSON Schema has:

- required `path`: non-blank string relative to the workspace;
- optional `max_depth`: integer from 1 through the configured hard limit;
- `max_depth` defaults to 2;
- no additional properties.

Depth semantics are explicit:

- `max_depth=1` returns only the requested directory's direct children;
- `max_depth=2` also returns their direct children;
- the default hard limit is 3 and can be reduced or injected for tests.

The tool has a positive configurable maximum entry count, defaulting to 500.
Reaching the limit returns a successful, explicitly truncated result rather
than scanning or returning an unbounded tree.

## Result Shape

Successful results provide both model-readable text and structured data.

Each entry contains:

- `path`: normalized workspace-relative POSIX path;
- `name`: the final path component;
- `type`: `file`, `directory`, or `symlink`;
- `size_bytes`: file size for regular files and `null` otherwise.

Entries are deterministically ordered by case-folded normalized relative POSIX
path, with the original relative path as the tie-breaker. The text `content` is
a stable line-oriented representation of the same entries so a later Agent
Loop can consume it without depending on a frontend or API.
`data.entries` contains the structured entries. `metadata` contains the
requested root path, applied depth, returned entry count, and `truncated`.

An empty permitted directory returns success with empty content and an empty
entry list.

## Traversal And Limits

Directory work runs through `asyncio.to_thread` so synchronous filesystem
metadata access does not block the event loop.

Traversal is deterministic and bounded:

1. Validate the requested path against the configured workspace.
2. Confirm the resolved path exists and is a regular directory.
3. Enumerate safe entries without following symbolic links.
4. Sort entries before collecting or descending.
5. Descend only into ordinary directories while respecting `max_depth`.
6. Stop as soon as the configured maximum entry count is reached and mark the
   result truncated.

Symbolic links may be reported as `symlink`, but their targets are never read,
resolved for traversal, or recursively followed. Unsupported special file
types are omitted.

## Security And Error Handling

The requested root path reuses `resolve_workspace_path`, including rejection
of absolute paths, drive-qualified and UNC paths, parent traversal, alternate
data streams, sensitive components, and paths resolving outside the workspace.

Traversal filters sensitive child names before metadata collection or
recursion. The shared filter covers:

- `.git`, `.ssh`, and `docs-local` directories;
- `.env` and `.env.*` files;
- common private key names;
- `.pem` and `.key` files;
- `__pycache__` directories.

Ordinary dotfiles such as `.gitignore` remain visible. The existing private
sensitive-component check will become a small public security helper so both
`resolve_workspace_path` and `list_dir` use one policy instead of duplicating
rules.

All expected failures return a failed `ToolResult` with a fixed safe message:

- invalid arguments;
- unsafe path;
- missing path;
- non-directory path;
- permission or other filesystem error.

Failures do not echo raw arguments, absolute paths, exception strings,
directory entries, or secret-like values. Per-request validation errors remain
Tool results rather than uncaught exceptions. Invalid constructor
configuration still fails fast with `TypeError` or `ValueError`.

## Registry Integration

`register_builtin_tools()` remains caller-controlled and side-effect free at
import time. It will construct and register tools in this order:

1. `read_file`
2. `list_dir`

The helper accepts the existing read-file limits plus list-dir maximum depth
and maximum entry count, sharing the same injected workspace root. Registry
listing and OpenAI-compatible schema export must expose both tools in that
stable order. Existing duplicate-registration errors remain explicit; no
singleton or application-startup registration is introduced.

## TDD And Verification

Implementation follows three RED/GREEN slices matching the requested Steps:

1. **S4:** metadata/schema, default and explicit depth, recursive results,
   name/type/size, deterministic ordering, empty directories, and truncation.
2. **S5:** invalid and unsafe paths, sensitive filtering, non-followed
   symlinks, missing/non-directory paths, permission and generic filesystem
   failures, and absence of sensitive details in results.
3. **S6:** builtin registration order, injected configuration,
   OpenAI-compatible schemas, and duplicate-registration behavior.

Verification includes:

- focused `list_dir` tests after each RED/GREEN slice;
- the complete Tool foundation suite;
- complete backend pytest and `pip check`;
- frontend typecheck, complete Vitest, and production build as regression
  checks;
- Markdown link/path checks, changed-file secret-pattern checks, generated
  artifact checks, `git diff --check`, and final clean-scope review.

Tests use temporary workspaces and synthetic sensitive names. They do not read
real secret files, real Provider credentials, or the user's SQLite database.

## Documentation And Acceptance Record

Update only documentation affected by the newly implemented Tool:

- `README.md` and `README_CN.md` current-stage/capability statements;
- `docs/00-project-overview.md`;
- `docs/01-architecture.md`;
- `docs/10-tool-calling-design.md`;
- the `P2-M2-S4` through `P2-M2-S6` rows and a dated acceptance record in the
  Plan 2 execution table.

The documentation must continue to state that `web_fetch`, Provider tool
calling, Agent Loop behavior, Agent APIs, and frontend Agent views are not yet
implemented. `CHANGELOG.md` is changed only if its existing unreleased policy
requires per-batch Plan 2 entries; release history is never rewritten.

## Completion Boundary

The batch is complete when `list_dir` is safely implemented and registered,
the specified tests and regressions pass, documentation reflects only the
implemented S4-S6 state, and Codex self-review finds no blocking issue or
Plan-boundary crossing. The user will perform any Git commit manually.
