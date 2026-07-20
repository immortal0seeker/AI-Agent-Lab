# LLM Provider And Model Registry

## Implemented Scope

Plan 1 Milestone 2 provides the backend foundation for model access, and
`P2-M3-S1` through `P2-M3-S8` extend its non-streaming protocol boundary and
add its first backend Agent consumer:

- vendor-neutral asynchronous chat and stream contracts
- typed messages, requests, responses, chunks, and token usage
- an OpenAI-compatible HTTP adapter
- environment-backed Provider initialization
- API-key masking and readable Provider errors
- a strict JSON Model Registry
- mock HTTP and Registry unit tests
- classified Provider failures with safe client messages
- successful Chat usage, Registry cost, and latency persistence
- typed function Tool definitions and normalized Tool Calls
- a defensive Tool Registry-to-Provider schema adapter
- OpenAI-compatible non-streaming `tools` serialization and `tool_calls` parsing
- Provider-neutral assistant Tool Call and correlated Tool observation messages
- a backend-only bounded Agent loop with AgentRun/ToolCall persistence,
  per-Tool timeouts, and structured failure results

The Provider layer is consumed by both `POST /api/v1/chat/completions` and
`POST /api/v1/chat/stream`. `GET /api/v1/models` exposes read-only Registry
metadata, and the frontend selector uses its exact provider/model identities.
Listing models does not initialize a Provider or expose credentials.
`SimpleAgentService` also consumes the non-streaming contract directly. The
plural Agent create/query routes and read-only frontend audit workspace expose
that service synchronously.

## Provider Contract

`backend/app/providers/llm/base.py` defines:

- `ChatMessage`
- `ChatRequest`
- `LLMFunctionDefinition`
- `LLMToolDefinition`
- `LLMToolCall`
- `TokenUsage`
- `LLMResponse`
- `ChatChunk`
- `BaseLLMProvider`
- Provider-layer exception types

Future business services should depend on `BaseLLMProvider`, not on `httpx`, an OpenAI SDK, or a specific model vendor.

The current contract supports non-streaming chat, text-only streaming chunks,
text messages, model override, temperature, maximum output tokens, normalized
token usage, typed function Tool definitions, and normalized non-streaming Tool
Calls. `ChatRequest.tools` defaults to an empty tuple, preserving ordinary Plan
1 payloads. `LLMResponse` requires text content, at least one Tool Call, or both;
Tool Call IDs must be unique in one response. JSON-mode request fields remain
deferred.

`ChatMessage` now represents four validated Provider-neutral shapes: system or
user text, assistant text, assistant Tool Calls, and Tool observations carrying
the matching `tool_call_id`. Invalid role/field combinations and duplicate
assistant Tool Call IDs are rejected locally. `LLMToolCall.arguments` must be a
standard JSON-serializable object even when constructed by a Mock or future
non-OpenAI adapter.

## Tool Definition Adapter

`backend/app/providers/llm/tool_adapter.py` converts a caller-owned
`ToolRegistry` into `LLMToolDefinition` values in Registry order. Each
definition copies the Tool name, description, and object-root parameter schema.
The adapter does not execute tools, inspect the workspace, mutate the Registry,
or depend on builtin Tool classes. Registry schemas and serialized Provider
definitions remain independent defensive values.

Tool names accept at most 64 ASCII letters, digits, underscores, or hyphens.
Parameter schemas must have an object root and be strict JSON-serializable;
non-standard numeric values are rejected. The adapter intentionally does not
emit OpenAI `strict=true`, because the existing Draft 2020-12 schemas do not
claim the narrower strict-mode subset.

## OpenAI-Compatible Configuration

Provider settings are optional while the application only serves health checks. They are validated when `create_openai_compatible_provider()` initializes an adapter.

| Environment variable | Purpose | Example value |
|---|---|---|
| `OPENAI_COMPATIBLE_BASE_URL` | API root before `/chat/completions` | `https://api.example.com/v1` |
| `OPENAI_COMPATIBLE_API_KEY` | Local Provider credential | empty in tracked examples |
| `OPENAI_COMPATIBLE_MODEL` | Default model identifier | `example-model` |
| `OPENAI_COMPATIBLE_TIMEOUT_SECONDS` | Request timeout | `30` |
| `AGENT_RUN_TIMEOUT_SECONDS` | Whole Simple Agent run timeout | `120` |
| `MODEL_REGISTRY_PATH` | Optional local Registry JSON override | empty uses tracked default |

Keep real credentials only in a local untracked `.env` file or process
environment. Settings store the key as Pydantic `SecretStr`. Provider HTTP
errors do not incorporate upstream response bodies, so echoed credentials or
diagnostic content cannot propagate through the application exception message.

Missing keys fail at Provider initialization with a readable `ProviderConfigurationError`; they do not prevent the health-only application from starting.

## OpenAI-Compatible Adapter

`OpenAICompatibleProvider` posts to `<base_url>/chat/completions` with bearer authentication. It maps common OpenAI-compatible request fields and normalizes response usage:

```text
prompt_tokens     -> input_tokens
completion_tokens -> output_tokens
total_tokens      -> total_tokens
```

Streaming sends `stream=true`, reads `data:` SSE lines, yields `ChatChunk`
values, and stops at `[DONE]`. Transport failures, non-success HTTP responses,
malformed JSON, and malformed response shapes become Provider-layer exceptions.
Authentication, rate limit, timeout, bad request, upstream server, invalid
response, and unknown request failures have distinct classes. The adapter never
propagates the upstream error body through its exception message.

For non-streaming requests, non-empty `ChatRequest.tools` serialize to the
OpenAI-compatible `tools` array; empty tools are omitted. Response
`message.tool_calls` values are parsed in Provider order into tool-call ID,
function name, and object arguments. Arguments must be a standard JSON string
whose root is an object. Missing/invalid fields, non-function calls,
non-standard JSON constants, duplicate IDs, and Tool Calls returned when none
were requested all produce the fixed safe `ProviderResponseError` boundary;
raw arguments never enter the exception message.

For the follow-up request after execution, the adapter serializes normalized
assistant Tool Calls back to OpenAI-compatible `id/type/function` values and
encodes arguments as deterministic compact standard JSON. Each Tool observation
uses `role="tool"`, string content, and the corresponding `tool_call_id`.
These wire details remain isolated from the Agent service.

Streaming Tool Calls are not implemented in this batch. `stream_chat()` rejects
a request containing tools with `ProviderUnsupportedFeatureError` before any
HTTP I/O instead of silently dropping or partially reconstructing deltas.

Retry and fallback policies remain deferred. Milestone 4 provides
request-linked safe logs and manual frontend initialization recovery, but it
does not create Provider retry policy or a persistent Trace system.

## Usage, Cost, And Latency

Both Chat paths persist a completed `LLMCall` only after successful Provider
completion. Provider usage maps directly to `input_tokens`, `output_tokens`,
and `total_tokens`. The workspace does not estimate tokens when usage is absent.

Estimated cost uses the exact `Decimal` prices from the selected Registry entry:

```text
(input_tokens × input_price_per_1m
 + output_tokens × output_price_per_1m) / 1_000_000
```

The value is rounded to the database's eight-decimal scale. If usage or either
price is unknown, cost remains `NULL`; explicit zero prices produce zero cost.
Latency covers Provider waiting only. Streaming accumulates time spent awaiting
chunks and excludes pauses while the downstream SSE consumer processes them.

Provider failure, invalid empty streams, database failure, and client
cancellation do not persist the incomplete turn or a failed `LLMCall`.

## Error Response Safety

Ordinary HTTP errors and terminal SSE error events share a structured envelope
with a safe code, fixed readable message, and server-generated request ID. The
same ID is returned in `X-Request-ID` and included in request/model-call logs.
Logs never include complete messages, credentials, upstream response bodies, or
SQL parameters.

## Model Registry

The default tracked Registry configuration is
`backend/app/providers/llm/models.json`. It contains one clearly named example
OpenAI-compatible model aligned with `backend/.env.example`. The entry is
scaffolding and does not claim that a real model endpoint was tested.

For local Tool-capable development, copy the tracked secret-free
`models.local.example.json` to the ignored `models.local.json`, replace its
synthetic model identifier, and set `MODEL_REGISTRY_PATH` in untracked
`backend/.env`. An empty setting keeps the default file. Registry JSON must not
contain credentials.

Each model defines:

| Field | Meaning |
|---|---|
| `provider` | Provider identifier used with the model identity |
| `model` | Provider model identifier |
| `display_name` | Human-readable label |
| `supports_streaming` | Streaming implemented by this workspace for the entry |
| `supports_tools` | Tool Calling implemented by this workspace for the entry |
| `supports_json` | JSON-mode requests implemented by this workspace for the entry |
| `input_price_per_1m` | Optional input price; `null` when not maintained |
| `output_price_per_1m` | Optional output price; `null` when not maintained |

Capability labels describe project behavior for a configured model, not every
feature offered by an upstream endpoint. The tracked example marks streaming as
supported and leaves Tool Calling and JSON mode disabled. `P2-M3-S1` through
`P2-M3-S8` prove the non-streaming adapter and Agent service with mocks; they do
not verify that the example model supports tools. The backend service rejects a
model unless its selected Registry entry explicitly sets `supports_tools=true`,
so the tracked example cannot run the Agent path without an intentional local
configuration. Prices remain `null` instead of using invented or stale values.

Registry usage:

```python
from app.providers.llm.registry import load_default_registry

registry = load_default_registry()
models = registry.list_models()
filtered = registry.list_models(provider="openai_compatible")
model = registry.get_model("openai_compatible", "example-model")
```

The loader rejects unreadable files, invalid JSON, unknown fields, blank names, negative prices, and duplicate `(provider, model)` identities. Model metadata is immutable, and list calls return defensive copies.

## Verification

Run from `backend`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_base.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_llm_tool_adapter.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_provider.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_simple_agent.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_factory.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_llm_model_registry.py -q
..\.venv\Scripts\python.exe -m pytest -q
```

Tests use `httpx.MockTransport`, temporary Registry files, and fake test credentials. They do not call a real Provider or paid API.

Provider adapter tests cover typed definitions, Registry conversion,
non-streaming Tool request/response mapping, single and multiple calls,
malformed or non-standard arguments, no-I/O streaming rejection, ordinary
streaming, HTTP classification, timeout/transport failures, usage
normalization, and safe exception text. Chat service and API tests additionally
use mock Providers to verify SSE event framing, successful persistence,
classified HTTP/SSE error
envelopes, Provider failure rollback, cancellation rollback, and request-linked
safe logs. Conversation and isolated error-handler tests cover default creation,
malformed IDs, 405 responses, and unexpected 500 responses. Browser verification
intercepts health, Registry, conversation, and stream requests; it does not
require a real API key.

Simple Agent tests inject a tools-capable Mock Registry and disposable SQLite.
They cover direct answers, existing history, multiple ordered Tool rounds,
exact observation correlation, safe unknown/invalid/failed/malformed Tool
results, atomic ToolCall budgets, permission denial, cross-round ID reuse,
finite Tool/whole-run timeouts, bounded escaped observations, structured
Provider failures, cancellation propagation, strict ToolCall sequence, and
AgentRun/ToolCall commit/reload. They use only temporary
workspace files and never initialize a real Provider.

## Known Limitations

- The current local workflow uses an editable backend install, where `models.json` is loaded directly from the source tree. `backend/pyproject.toml` does not yet declare the JSON file as setuptools package data, so a future wheel or sdist workflow must add and verify that packaging configuration.
- Registry validation exceptions may still contain Pydantic field context internally. `models.json` must not contain credentials or other sensitive values; API errors and logs intentionally expose only a fixed safe message and exception type.
- Agent Provider calls are not yet represented by Agent-linked `LLMCall` rows, so their usage/cost and Provider replay are not persisted in this batch.
- ToolCall order is persisted through `sequence_index`, but there is no later-Plan AgentStep/Trace timeline.
- The Agent service flushes but does not commit. Completed and structured failed results remain committable; M4 API code owns the transaction and response mapping. Database errors and task cancellation still propagate for caller-owned rollback.
- The Simple Agent enforces an atomic total ToolCall budget and read-only permission boundary. Calls remain sequential; broader Runtime/Approval policy belongs to later Plans.

## Deferred Work

- conversation rename/delete, search, and pagination
- Markdown rendering
- Provider retries and fallback policy
- persistent Trace, Timeline, and replay
- streaming Tool Call delta aggregation
- Agent automatic retry/cancel/resume policy and a broader Runtime Policy
- AgentRun list/polling and later runtime controls
- all later-plan capabilities
