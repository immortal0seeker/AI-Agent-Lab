# Tool Calling Design

## Current Scope

Plan 2 M1 establishes Tool contracts, discovery, validation, read-only security,
and persistence models. `P2-M2-S1` through `P2-M2-S7` complete M2 with two
executable read-only builtins, `read_file` and `list_dir`, plus caller-controlled
Registry initialization and an explicit `web_fetch` deferral. No Agent service,
API, or Provider currently invokes a Tool.

## Tool Boundary

`Tool` owns normalized metadata, a JSON parameter schema, permission label,
timeout, and asynchronous `run(arguments) -> ToolResult`. Definition metadata
is read-only after construction, and each parameter-schema read returns a deep
copy so a registered Tool cannot drift from its Registry key or exported
schema. Tool names are at most 64 ASCII letters, digits, underscores, or
hyphens. `ToolResult` keeps success, content, structured data, error, and
metadata consistent. ToolCall transport schemas keep Provider correlation IDs
separate from ORM identities.

## Registry and Validation

`ToolRegistry` registers exact names, rejects duplicates, preserves order, and
exports defensive OpenAI-compatible function schemas. Registered parameter
schemas must be JSON-serializable Draft 2020-12 schemas with an explicit
`type: object` root. Argument validation runs before future execution.
Validation errors contain safe paths and rules and never echo rejected
argument or schema values.

## Read-only Security

Paths are workspace-relative and resolved before use. Absolute, drive, UNC,
parent traversal, `.env`, credential files/directories, private keys, Windows
path aliases, and alternate data streams are rejected. Credential policy
includes package-manager credentials, Git credential stores, cloud CLI config,
container/Kubernetes config, and common credential JSON names while ordinary
dotfiles such as `.gitignore` remain available. File-size and directory-depth
limits are shared policy helpers. The security module itself does not read or
enumerate files; each builtin owns its bounded filesystem operation.

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

## Built-in list_dir

`ListDirTool` accepts a required workspace-relative `path` and optional integer
`max_depth`. Depth 1 lists direct children, depth 2 includes one more level,
the default is 2, and the configured hard limit is at most 3. Traversal returns
at most 500 entries by default and marks bounded results as truncated.

Each entry contains a normalized relative path, name, `file`, `directory`, or
`symlink` type, and byte size for regular files. Results are globally ordered
by case-folded relative POSIX path with the original path as tie-breaker.
Line-oriented `content` and structured `data.entries` carry the same listing;
metadata records root path, applied depth, entry count, and truncation state.

Sensitive names including `.git`, `.ssh`, `.aws`, `.azure`, `.kube`, `.docker`,
`.gnupg`, `docs-local`, `__pycache__`, `.env*`, package-manager/Git credential
files, private-key names, `*.pem`, and `*.key` are filtered before metadata
access or recursion. Ordinary `.gitignore` remains visible. Discovered symlinks
and Windows reparse points such as directory junctions are reported with the
stable `symlink` entry type but are never followed and never expose their
target. `truncated` is true only when at least one additional visible entry was
not returned. Invalid, unsafe, missing, non-directory, and filesystem failure
paths return fixed safe ToolResults. Directory metadata work runs through
`asyncio.to_thread`.

`register_builtin_tools(registry, ...)` adds configured `ReadFileTool` and
`ListDirTool` instances, in that order, to a caller-owned Registry. It creates
no singleton and has no import-time or application-startup side effect.
Configuration and duplicate-name checks happen before either Tool is added, so
an initialization failure leaves the caller's Registry unchanged.

## web_fetch Deferral

`P2-M2-S7` evaluated `web_fetch` and explicitly deferred it. No
`web_fetch.py`, Tool/schema registration, URL helper, dependency, API, or UI is
implemented. A safe network Tool requires a complete scheme/port policy,
public-address and DNS-rebinding strategy, redirect revalidation, strict
timeouts, bounded streaming, content-type/decoding rules, safe HTML text
extraction, redacted errors, and mock coverage. Implementing a subset would
misrepresent the Tool as low risk.

The capability may be reassessed in Plan 4 or Plan 6, but neither Plan is
committed to this exact Tool shape. The active future Step must approve the
network permission and extraction contract before implementation.

## Persistence

`AgentRun` records Conversation ownership, an optional user Message, simple
status, goal/final output/error, timing, and creation time. `ToolCall` uses a UUID
database ID plus a separate string `tool_call_id`, belongs to an AgentRun, keeps
direct Conversation lookup, stores JSON arguments/result, and records status and
timing. Composite and unique constraints prevent cross-Conversation ownership
and duplicate correlation IDs inside one run. An AgentRun's optional user
Message is also protected by a composite key and must belong to the same
Conversation; migration stops safely if historical rows violate that rule or
contain a non-null Message ID that no longer exists.

Deleting a Conversation removes its runs and calls. Deleting one user Message
keeps the audit record and nulls its link. Deleting an AgentRun removes its
ToolCalls.

## Status Values

AgentRun: `created`, `running`, `waiting_tool`, `completed`, `failed`,
`cancelled`.

ToolCall: `pending`, `running`, `success`, `failed`, `timeout`, `blocked`.

These are integrity values, not a full runtime state machine.

## Current Data Flow

The implemented builtin path is:

```text
Caller-owned Registry
-> ReadFileTool or ListDirTool
-> argument and workspace security validation
-> bounded read or directory traversal
-> ToolResult
```

No current route or service invokes the Tool or creates AgentRun/ToolCall
records. Provider integration, Agent Loop transitions, API access, and frontend
visualization are scheduled in later Plan 2 milestones. Provider Tool Calling
in `P2-M3-S1` through `P2-M3-S3` is the next implementation boundary.

## Verification and Security Boundary

Tests use Mock Tools, `tmp_path`, the tracked repository `README.md`, and
disposable SQLite databases. They do not read a real `.env`, user database,
credential, private key, or call a real Provider.

## Deferred Work

- Agent persistence service and transactions
- `web_fetch` reassessment, no earlier than Plan 4 or Plan 6
- Provider tool calling
- Simple Agent Loop
- Agent APIs and frontend ToolCall visualization
- Plan 4 Trace, replay, and evaluation
