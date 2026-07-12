# Plan 1 M3 Non-Streaming Chat Design

## Scope

This design covers only `P1-M3-S1` through `P1-M3-S3`:

- Conversation Service creation, lookup, message append, and ordered message reads
- non-streaming Chat Service orchestration
- request-scoped SQLAlchemy transaction handling
- Provider selection through a provider mapping and model validation through Model Registry
- Conversation and non-streaming Chat API routes
- focused service, API, persistence, rollback, and error-path tests

API-level streaming, frontend Chat, conversation lists/history APIs, token-cost-latency recording, detailed error taxonomy, Tool Calling, and later-plan capabilities are outside this batch.

## Request Model

The client submits only the current user turn:

```json
{
  "conversation_id": null,
  "provider": "openai_compatible",
  "model": "example-model",
  "content": "Hello",
  "temperature": 0.7,
  "max_tokens": null
}
```

The backend owns persisted conversation history. It loads prior messages, appends the new user message, and sends the resulting ordered history to `BaseLLMProvider.chat()`. This prevents the frontend and SQLite history from becoming competing sources of truth.

## Service Boundaries

`ConversationService` owns synchronous database operations:

- `create_conversation(data) -> Conversation`
- `get_conversation(conversation_id) -> Conversation`
- `append_message(data) -> Message`
- `list_messages(conversation_id) -> list[Message]`

Missing conversations raise `ConversationNotFoundError`. Methods add and flush ORM objects but do not commit, allowing Chat Service to compose one transaction.

`ChatService` owns asynchronous orchestration:

1. Resolve `(provider, model)` in `ModelRegistry`.
2. Resolve the provider adapter from an injected mapping.
3. Load or create the conversation.
4. Append and flush the user message.
5. Load ordered persisted history and map it to Provider `ChatMessage` values.
6. Await `BaseLLMProvider.chat()`.
7. Append the assistant message and a successful `LLMCall`.
8. Return a typed service result.

The Registry validates model selection; the provider mapping routes a provider identifier to an adapter. This batch supports the configured `openai_compatible` adapter without hard-coding it into business logic.

## Transaction Boundary

The request-scoped database dependency owns commit/rollback:

```text
request starts -> yield Session -> services flush -> endpoint returns -> commit
request error  -> rollback -> re-raise -> API error response
```

Chat Service also rolls back before re-raising Provider failures so direct service callers receive the same atomic behavior. A failed model call leaves no newly created conversation, user message, assistant message, or `LLMCall`.

The synchronous SQLite transaction remains open during the asynchronous Provider call. This is acceptable for the current local-first, primarily single-user architecture. If concurrency requirements change, the transaction strategy should be revisited rather than prematurely adding a queue or async database stack.

## Persistence

A successful call stores:

- a conversation when `conversation_id` is absent
- one user message
- one assistant message
- one `LLMCall` linked to the assistant message with status `completed`

`LLMCall.provider` stores the selected provider and `LLMCall.model` stores the actual response model. Token usage is returned to the caller but is not persisted in this batch because token/cost/latency recording belongs to `P1-M4-S1`.

Existing conversation messages are ordered by `created_at` and `id` before Provider conversion. Only Plan 1 text roles already accepted by `ChatMessage` are sent.

## API Contract

This batch adds:

```text
POST /api/v1/conversations
GET  /api/v1/conversations/{conversation_id}
POST /api/v1/chat/completions
```

The Chat response contains:

- `conversation_id`
- `user_message`
- `assistant_message`
- `provider`
- actual response `model`
- optional normalized `usage`
- `llm_call_id`

Routes validate schemas, call services, and shape responses. They do not contain persistence or Provider logic.

## Error Mapping

Basic readable API mappings are introduced without implementing the detailed M4 taxonomy:

- missing conversation -> HTTP 404
- unknown Registry model -> HTTP 400
- model exists but provider adapter is unavailable -> HTTP 503
- Provider configuration failure -> HTTP 503
- other Provider failures -> HTTP 502
- schema validation failure -> HTTP 422

No exception response includes API keys. M4 may replace these basic handlers with the project-wide standardized error envelope.

## Test Design

Implementation follows red-green-refactor cycles. Tests cover:

1. Conversation creation, lookup, append, ordering, and missing lookup.
2. New-conversation Chat success with Provider request capture.
3. Existing conversation history is included in the next Provider call.
4. Successful assistant message and `LLMCall` persistence.
5. Unknown model and unavailable provider failures.
6. Provider failure rolls back all new records.
7. OpenAPI exposes the three routes.
8. Conversation API success and 404 behavior.
9. Chat API success, response shape, persistence, and basic errors.
10. Existing backend and frontend checks remain green.

All Provider calls use mocks. Tests use temporary SQLite databases and fake credentials only.

## Review Cadence

M3 batches receive Codex self-review and automated/manual verification only. Per the user's review-cost decision, the next consolidated Fable 5 review occurs after M4 is complete.

## Deferred Work

- SSE endpoint and streaming persistence
- frontend Chat state and UI
- conversation list and message-history APIs
- model selector and refresh recovery
- token/cost/latency persistence
- detailed error envelope, retries, and logging
- Tool Calling and all later-plan capabilities
