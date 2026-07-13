# LLM Provider And Model Registry

## Implemented Scope

Plan 1 Milestone 2 provides the backend foundation for model access:

- vendor-neutral asynchronous chat and stream contracts
- typed messages, requests, responses, chunks, and token usage
- an OpenAI-compatible HTTP adapter
- environment-backed Provider initialization
- API-key masking and readable Provider errors
- a strict JSON Model Registry
- mock HTTP and Registry unit tests
- classified Provider failures with safe client messages
- successful Chat usage, Registry cost, and latency persistence

The Provider layer is consumed by both `POST /api/v1/chat/completions` and
`POST /api/v1/chat/stream`. `GET /api/v1/models` exposes read-only Registry
metadata, and the frontend selector uses its exact provider/model identities.
Listing models does not initialize a Provider or expose credentials.

## Provider Contract

`backend/app/providers/llm/base.py` defines:

- `ChatMessage`
- `ChatRequest`
- `TokenUsage`
- `LLMResponse`
- `ChatChunk`
- `BaseLLMProvider`
- Provider-layer exception types

Future business services should depend on `BaseLLMProvider`, not on `httpx`, an OpenAI SDK, or a specific model vendor.

The current contract supports non-streaming chat, streaming chunks, text messages, model override, temperature, maximum output tokens, and normalized token usage. Tool Calling and JSON-mode request fields are intentionally absent because they belong to later work.

## OpenAI-Compatible Configuration

Provider settings are optional while the application only serves health checks. They are validated when `create_openai_compatible_provider()` initializes an adapter.

| Environment variable | Purpose | Example value |
|---|---|---|
| `OPENAI_COMPATIBLE_BASE_URL` | API root before `/chat/completions` | `https://api.example.com/v1` |
| `OPENAI_COMPATIBLE_API_KEY` | Local Provider credential | empty in tracked examples |
| `OPENAI_COMPATIBLE_MODEL` | Default model identifier | `example-model` |
| `OPENAI_COMPATIBLE_TIMEOUT_SECONDS` | Request timeout | `30` |

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

Retry and fallback policies remain deferred. The current Milestone 4 batch adds
request-linked safe logs but does not create a persistent Trace system.

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

The default tracked Registry configuration is `backend/app/providers/llm/models.json`. It contains one clearly named example OpenAI-compatible model aligned with `backend/.env.example`. The entry is scaffolding and does not claim that a real model endpoint was tested.

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

Capability labels describe project behavior, not every feature offered by an upstream model. Plan 1 currently marks streaming as supported and leaves Tool Calling and JSON mode disabled. Prices remain `null` instead of using invented or stale values.

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
..\.venv\Scripts\python.exe -m pytest tests/test_openai_compatible_provider.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_llm_provider_factory.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_llm_model_registry.py -q
..\.venv\Scripts\python.exe -m pytest -q
```

Tests use `httpx.MockTransport`, temporary Registry files, and fake test credentials. They do not call a real Provider or paid API.

Chat service and API tests additionally use mock Providers to verify SSE event
framing, successful persistence, Provider failure rollback, and cancellation
rollback. Browser verification intercepts health and stream requests; it does
not require a real API key.

## Known Limitations

- The current local workflow uses an editable backend install, where `models.json` is loaded directly from the source tree. `backend/pyproject.toml` does not yet declare the JSON file as setuptools package data, so a future wheel or sdist workflow must add and verify that packaging configuration.
- Registry validation exceptions may still contain Pydantic field context internally. `models.json` must not contain credentials or other sensitive values; API errors and logs intentionally expose only a fixed safe message and exception type.

## Deferred Work

- conversation rename/delete, search, and pagination
- Markdown rendering
- Provider retries and fallback policy
- persistent Trace, Timeline, and replay
- Tool Calling and all later-plan capabilities
