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

This layer is not exposed through a Chat or Models API yet. Services, API routes, persistence, and frontend model selection start in later Plan 1 milestones.

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

Keep real credentials only in a local untracked `.env` file or process environment. Settings store the key as Pydantic `SecretStr`. Provider HTTP errors redact the configured key if an upstream error unexpectedly echoes it.

Missing keys fail at Provider initialization with a readable `ProviderConfigurationError`; they do not prevent the health-only application from starting.

## OpenAI-Compatible Adapter

`OpenAICompatibleProvider` posts to `<base_url>/chat/completions` with bearer authentication. It maps common OpenAI-compatible request fields and normalizes response usage:

```text
prompt_tokens     -> input_tokens
completion_tokens -> output_tokens
total_tokens      -> total_tokens
```

Streaming sends `stream=true`, reads `data:` SSE lines, yields `ChatChunk` values, and stops at `[DONE]`. Transport failures, non-success HTTP responses, malformed JSON, and malformed response shapes become Provider-layer exceptions.

Detailed error classes, retry policy, logging, latency, and cost recording remain scheduled for Milestone 4.

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

## Known Limitations

- The current local workflow uses an editable backend install, where `models.json` is loaded directly from the source tree. `backend/pyproject.toml` does not yet declare the JSON file as setuptools package data, so a future wheel or sdist workflow must add and verify that packaging configuration.
- Registry validation errors currently include Pydantic field context and rejected input values. `models.json` must not contain credentials or other sensitive values. Milestone 4 error handling should evaluate redacted or summarized validation messages before these errors are written to application logs.

## Deferred Work

- Models and Chat API routes
- Conversation and Chat services
- frontend model selection and Chat UI
- persistence and API-level SSE
- detailed Provider error taxonomy, retries, logging, cost, and latency
- Tool Calling and all later-plan capabilities
