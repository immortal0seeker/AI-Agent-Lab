# Plan 1 M2 LLM Provider Design

## Scope

This design covers only `P1-M2-S4` through `P1-M2-S6`:

- a vendor-neutral asynchronous LLM Provider contract
- typed chat request, response, streaming chunk, and token usage data
- an OpenAI-compatible HTTP adapter for non-streaming and SSE streaming calls
- provider configuration and readable missing-key handling
- mock HTTP tests that require no real provider credentials or paid API calls

Model Registry, Chat services and routes, persistence, frontend Chat, Tool Calling, and later-plan capabilities are outside this batch.

## Architecture

The provider layer follows these ownership boundaries:

- `app/providers/llm/base.py` owns vendor-neutral contracts and base errors.
- `app/providers/llm/openai_compatible.py` translates those contracts to and from OpenAI-compatible HTTP payloads.
- `app/providers/llm/factory.py` translates application settings into a configured provider instance.
- `app/core/config.py` owns environment-backed provider settings.

The dependency direction is:

```text
Settings -> provider factory -> OpenAI-compatible adapter
Future chat service -> BaseLLMProvider -> typed response or stream
OpenAI-compatible HTTP -> adapter -> vendor-neutral contracts
```

No route or service imports a vendor SDK. `httpx` is the only HTTP dependency and is injected in tests through `MockTransport`.

## Provider Contract

`ChatMessage` contains a Plan 1 chat role and text content. `ChatRequest` contains messages, an optional model override, temperature, and optional maximum output tokens. A provider-level default model is used when the request does not override it.

`LLMResponse` contains the provider response identifier, resolved model, assistant content, finish reason, and optional normalized token usage. `ChatChunk` contains the corresponding streaming delta fields and optional usage from a final usage-bearing chunk.

`BaseLLMProvider` exposes:

```python
async def chat(request: ChatRequest) -> LLMResponse
def stream_chat(request: ChatRequest) -> AsyncIterator[ChatChunk]
```

The stream method is part of the provider contract in this batch because the source Plan 1 design includes it in the Provider step. This does not add an SSE API endpoint; the Chat API stream remains in M3.

Tool arguments, JSON mode, retries, model capability metadata, and registry behavior are deliberately absent. They belong to later steps or plans.

## OpenAI-Compatible Adapter

The adapter sends bearer-authenticated requests to `<base_url>/chat/completions`. It normalizes trailing slashes, serializes only supported request fields, maps non-streaming `choices[0].message.content`, and converts OpenAI usage names to the project token usage structure.

Streaming uses the same request with `stream=true`, parses `data:` SSE lines, stops at `[DONE]`, and yields typed chunks. Empty transport keep-alive lines are ignored.

An injected `httpx.AsyncClient` is never closed by the provider. When no client is injected, the provider creates and closes a short-lived client per call. Persistent client lifecycle management can be added with the future service/application lifespan when there is a real call path.

## Configuration And Errors

Backend settings add:

- `OPENAI_COMPATIBLE_BASE_URL`
- `OPENAI_COMPATIBLE_API_KEY`
- `OPENAI_COMPATIBLE_MODEL`
- `OPENAI_COMPATIBLE_TIMEOUT_SECONDS`

The API key uses Pydantic `SecretStr`, is never included in error messages, and may remain unset while the health-only application starts. Provider initialization fails with a readable `ProviderConfigurationError` when a call path attempts to create a provider without a key. Base URL, model, and timeout are also validated at provider construction.

Transport failures, non-success HTTP responses, and malformed successful responses are translated to Provider-layer exceptions. Fine-grained auth, rate-limit, timeout, and server-error classes are deferred to `P1-M4-S2`; this batch provides a stable readable base boundary without implementing that later Step early.

## Test Design

Implementation follows red-green-refactor cycles. Tests cover:

1. A mock provider implementing the common contract.
2. Contract validation for messages, temperature, and maximum tokens.
3. Non-streaming request serialization and response/usage parsing.
4. SSE chunk parsing and `[DONE]` termination.
5. Model override and configured default model behavior.
6. Missing API key handling without leaking secrets.
7. HTTP and malformed-response error translation.
8. Existing backend and frontend checks remain green.

All adapter tests use `httpx.MockTransport`. No test reads a local `.env` file or contacts a real provider.

## Documentation And Dependency Updates

`httpx` moves from the development-only group to backend runtime dependencies in both dependency manifests. The backend environment example, README files, architecture/overview docs, and Batch 5 execution-table status are updated without claiming a real paid API call was performed.

## Deferred Work

- Model Registry and model listing API (`P1-M2-S7` through `P1-M2-S8`)
- Chat services, routes, persistence, and API-level SSE (`P1-M3`)
- detailed error taxonomy, retries, logging, latency, and cost handling (`P1-M4`)
- Tool Calling and all later-plan capabilities
