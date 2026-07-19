# Tool Calling Design

## Current Scope

Plan 2 M1 establishes Tool contracts, discovery, validation, read-only security,
and persistence models. `P2-M2-S1` through `P2-M2-S7` complete M2 with two
executable read-only builtins, `read_file` and `list_dir`, plus caller-controlled
Registry initialization and an explicit `web_fetch` deferral. `P2-M3-S1`
through `P2-M3-S6` add typed non-streaming Provider Tool definitions and Tool
Calls, a Registry-to-Provider adapter, safe OpenAI-compatible request/response
mapping, and a backend-only Simple Agent service that executes one Tool round
and persists AgentRun/ToolCall rows. No Agent API or frontend view exists yet.

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
`type: object` root. Argument validation runs before execution.
Validation errors contain safe paths and rules and never echo rejected
argument or schema values.

`build_llm_tool_definitions(registry)` is the typed Provider boundary. It
copies the ordered Tool name, description, and object-root parameter schema
into frozen-top-level `LLMToolDefinition` values without executing a Tool or
depending on builtin implementations. Nested schema inputs are defensively
copied, and mutating a serialized definition cannot change the Registry or a
later conversion.

## Provider Tool Calling Boundary

`ChatRequest.tools` is an ordered tuple and defaults to empty, so ordinary Chat
payloads still omit `tools`. `LLMResponse` can carry text, normalized
`LLMToolCall` values, or both; every Tool Call has a Provider correlation ID,
validated function name, and already parsed object arguments. Multiple calls
preserve Provider order and duplicate IDs are rejected.

`ChatMessage` validates ordinary text, assistant Tool Call, and Tool observation
shapes without exposing OpenAI field dictionaries to the Agent service.
Assistant Tool Calls and observations preserve correlation IDs. Manually
constructed Tool arguments must also be standard JSON-serializable objects.

The OpenAI-compatible adapter serializes non-empty Tool definitions only for
non-streaming chat and parses `choices[0].message.tool_calls`. Function
arguments must be a standard JSON string with an object root. Invalid shapes,
non-standard constants, unrequested Tool Calls, or invalid/duplicate IDs become
a fixed `ProviderResponseError` without raw argument or upstream-body leakage.

For the follow-up request, the same adapter maps normalized assistant Tool Calls
back to `id/type/function` wire objects and emits each observation as a
`role="tool"` message with string content and the corresponding
`tool_call_id`. Arguments and observations use compact standard JSON.

Streaming Tool Call aggregation is intentionally absent. A tools-bearing
`stream_chat()` request raises `ProviderUnsupportedFeatureError` before HTTP.
The tracked example model remains `supports_tools=false`: mock protocol support
does not assert a real model capability. `SimpleAgentService` requires an
explicitly tools-capable Registry entry before it writes an AgentRun.

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

`SimpleAgentService` now creates the AgentRun, user/final assistant Messages,
and one ToolCall row before each attempted lookup/validation/execution. Safe
success or failure ToolResults determine terminal ToolCall fields. The service
flushes but never commits; the future Agent API owns that transaction boundary.
It does not create LLMCall rows because those rows currently have no AgentRun
association.

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

The implemented Provider transport path is:

```text
Caller-owned Registry
-> build_llm_tool_definitions()
-> ChatRequest.tools
-> OpenAI-compatible payload.tools
-> Provider message.tool_calls
-> normalized LLMToolCall objects
```

The implemented Simple Agent path is:

```text
SimpleAgentRequest
-> tools-capable model and Provider gate
-> Conversation + user Message + AgentRun
-> provider.chat(history + Registry definitions)
   -> direct final text
   -> ordered Tool Calls
      -> Tool lookup + schema validation + sequential execution
      -> one ToolCall row and observation per call
      -> provider.chat(assistant Tool Calls + observations)
      -> final text
-> assistant Message + completed AgentRun
```

The first Provider response may request multiple calls; they execute and return
observations in Provider order. The second Provider response must contain
non-blank final text and no further Tool Calls. A further call request ends with
a fixed `AgentLoopIncompleteError` and no third Provider call. General
`max_steps`, Tool timeout enforcement, retries, and comprehensive failure
returns belong to `P2-M3-S7`.

Unknown Tools, argument failures, failed ToolResults, exceptions, mismatched
Tool names, and non-standard JSON Tool results become safe failed observations.
Raw exception text and rejected argument values do not enter the observation or
ToolCall error. The existing Plan 1 text Chat path still sends no Tool
definitions and rejects Tool-only responses.

## Verification and Security Boundary

Tests use Mock Tools, `tmp_path`, the tracked repository `README.md`, and
disposable SQLite databases. They do not read a real `.env`, user database,
credential, private key, or call a real Provider.

The Agent suite additionally verifies direct and read_file loops, multiple-call
ordering, observation correlation, safe failures, two-call boundedness, and
AgentRun/ToolCall commit/reload. The database does not have an explicit ToolCall
sequence field, so only the runtime result promises strict order in this batch.

## Deferred Work

- `web_fetch` reassessment, no earlier than Plan 4 or Plan 6
- streaming Provider Tool Call aggregation
- general Agent max steps, Tool timeouts, retries, and failure-return policy
- Agent APIs and frontend ToolCall visualization
- Plan 4 Trace, replay, and evaluation
