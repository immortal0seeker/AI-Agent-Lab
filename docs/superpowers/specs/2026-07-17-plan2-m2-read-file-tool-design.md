# Plan 2 M2 Read File Tool Design

## Scope

This design covers only `P2-M2-S1` through `P2-M2-S3`:

- implement the built-in `read_file` Tool;
- cover its security and error behavior;
- provide caller-controlled registration in `ToolRegistry`.

It does not implement `list_dir`, `web_fetch`, Provider tool calling, an Agent
Loop, Agent persistence services, APIs, frontend views, RAG, Memory, or MCP.

## Architecture

`backend/app/tools/builtin/read_file.py` owns `ReadFileTool`. Its constructor
accepts an injected workspace root, byte limit, and returned-character limit.
Its public Tool parameter schema contains one required string field, `path`, and
rejects unknown properties. The Tool name is `read_file` and its permission
level is `read_only`.

`backend/app/tools/builtin/__init__.py` exports `ReadFileTool` and
`register_builtin_tools(registry, ...)`. The registration function adds a
configured `ReadFileTool` to a caller-owned Registry. It does not create global
state or connect the Registry to application startup.

The read operation runs through `asyncio.to_thread` so local file I/O does not
block the asynchronous Tool caller.

## Read Flow

```text
validate Tool arguments
-> resolve and validate the workspace-relative path
-> require an existing regular file
-> stat and enforce the byte limit
-> read at most the byte limit plus one and recheck the actual byte length
-> reject NUL content
-> decode UTF-8 or UTF-8 BOM strictly
-> truncate to the returned-character limit when needed
-> return ToolResult content and metadata
```

Path validation reuses the M1 security boundary. Absolute, drive-qualified,
UNC, parent-traversal, alternate-data-stream, `.env`, sensitive-directory, and
private-key paths remain forbidden. Only the resolved workspace-relative path
may appear in a successful result; absolute local paths are never returned.

## Limits and Encoding

The default byte limit remains `DEFAULT_MAX_FILE_BYTES` (`1 MiB`). The default
returned-character limit is `100_000`. Both limits are constructor-injected and
must be positive integers that are not booleans.

Files larger than the byte limit fail before their content is read. The actual
read requests at most `max_file_bytes + 1` bytes and checks that length in case
the file changed after `stat`, so a race cannot create an unbounded read. Files
within the byte limit but longer than the returned-character limit succeed with
truncated content and explicit metadata.

Only UTF-8 and UTF-8 with a BOM are supported. A BOM is removed during decoding.
NUL-bearing content and strict UTF-8 decoding failures are treated as unsupported
binary or non-UTF-8 content. No locale fallback, encoding guess, or new encoding
detection dependency is introduced.

## Result Contract

A successful result uses `ToolResult.content` for the returned text and includes:

```json
{
  "path": "README.md",
  "encoding": "utf-8",
  "size_bytes": 1234,
  "character_count": 1200,
  "returned_characters": 1200,
  "truncated": false
}
```

`character_count` describes the decoded text before truncation.
`returned_characters` describes the returned content. The path uses POSIX-style
workspace-relative separators for stable metadata across platforms.

Expected user, security, and filesystem failures return
`ToolResult(success=False)` with a fixed safe error. This includes invalid Tool
arguments, unsafe paths, missing paths, directories, oversized files, NUL or
non-UTF-8 content, permission failures, and ordinary `OSError` cases. Failure
messages do not echo argument values, file contents, absolute paths, or raw
exception text. Programmer errors are not silently converted into user errors.

## Registration

`register_builtin_tools()` accepts a `ToolRegistry` plus the same optional
workspace root and limit overrides as `ReadFileTool`. It constructs and
registers one `ReadFileTool`. Calling it twice on the same Registry preserves
the existing explicit duplicate-registration failure; it does not silently
replace or skip a Tool.

Later `P2-M2-S4` through `P2-M2-S6` may add `list_dir` to this initialization
function. This batch does not create the future implementation early.

## Testing

TDD coverage uses `tmp_path`, fake content, and injected limits. It covers:

- Tool metadata and strict parameter schema;
- UTF-8 and UTF-8 BOM reads;
- normalized success metadata and character truncation;
- isolated default/configuration validation;
- `.env`, private-key, traversal, and outside-workspace rejection;
- missing paths, directories, oversized files, NUL content, non-UTF-8 bytes,
  and `OSError`;
- safe failures that do not leak rejected content, absolute paths, or exception
  details;
- Registry listing and schema export after builtin initialization;
- duplicate builtin registration behavior.

Acceptance includes one safe smoke read of the repository `README.md`. It does
not read `.env`, credentials, user databases, or any sensitive local path.

After focused tests, verification runs the complete backend suite, `pip check`,
frontend typecheck, complete Vitest, and the production build. Documentation
link, secret-pattern, generated-artifact, Plan-boundary, and diff checks also
run before completion.

## Documentation

The batch updates README current-development scope, `docs/01-architecture.md`,
`docs/10-tool-calling-design.md`, and the Plan 2 execution table with verified
S1-S3 evidence. `CHANGELOG.md` remains unchanged because `v0.1.0` is still the
current release and Plan 2 is not released.

## Known Boundary

This is a local-first, single-user read-only Tool. Resolving the canonical path
before opening prevents ordinary symlink escape, but the design does not claim
to defend against a privileged hostile process racing filesystem entries during
the read. No write, delete, shell, network, Provider, or credential capability
is added.
