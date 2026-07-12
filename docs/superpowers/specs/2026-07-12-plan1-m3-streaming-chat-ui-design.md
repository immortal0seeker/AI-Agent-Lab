# Plan 1 M3 Streaming Chat And Basic UI Design

## Scope

This design covers only `P1-M3-S4` through `P1-M3-S6`:

- `POST /api/v1/chat/stream` using Server-Sent Events
- successful-completion-only streaming persistence
- rollback on Provider failure or client cancellation
- frontend Chat types and streaming API wrapper
- Zustand Chat state with send, stop, error, and new-chat behavior
- a responsive engineering-workspace Chat page
- backend, frontend, browser, and screenshot verification using mocks

Conversation list/history recovery, dynamic model selection, Markdown rendering, token/cost/latency persistence, detailed error envelopes, Tool Calling, and later-plan capabilities are outside this batch.

## SSE Protocol

The endpoint accepts the same `ChatCompletionRequest` as non-streaming Chat and returns `text/event-stream`:

```text
event: delta
data: {"content":"partial text"}

event: done
data: {ChatCompletionResponse JSON}

event: error
data: {"message":"readable error"}
```

`delta` may repeat zero or more times. Exactly one terminal `done` or `error` event ends a normal server stream. The frontend treats a connection ending without either terminal event as an error.

Events use compact JSON and UTF-8. The parser supports arbitrary network chunk boundaries and CRLF/LF separators.

## Streaming Transaction Lifecycle

Normal request-scoped yield dependencies cannot own a streaming transaction because their cleanup may happen outside the actual stream iteration. The streaming endpoint therefore receives a Session factory and creates one Session inside the response generator.

`ChatService.stream_complete()`:

1. validates Registry model and provider mapping
2. loads or creates the conversation
3. appends the new user message and builds persisted history
4. iterates `BaseLLMProvider.stream_chat()`
5. yields domain delta events while accumulating text, model, and usage
6. appends assistant message and completed `LLMCall`
7. commits before yielding the completed result

Provider failure, malformed/empty completion, cancellation, or generator close rolls back while the transaction is still uncommitted. The session is always closed by the SSE adapter.

On frontend stop, partial assistant text remains visible locally with a stopped state, but this turn is not stored in SQLite. A successful stream is persisted once, never chunk-by-chunk.

## Backend Boundaries

`ChatService` remains protocol-neutral and yields `ChatStreamDelta` or `ChatStreamCompleted`. It does not produce SSE strings.

`api/v1/chat.py` owns SSE encoding and converts service errors after streaming starts into an `error` event. The route itself only validates input, injects Registry/provider/session factory dependencies, and returns `StreamingResponse`.

Token usage may be included in the final response but remains unpersisted until M4.

## Frontend API And State

`frontend/src/types/chat.ts` owns API and UI types. `frontend/src/api/chat.ts` owns fetch, UTF-8 decoding, SSE framing, event validation, and AbortSignal support.

The Zustand store owns:

- current local messages
- optional persisted `conversationId`
- `idle`, `streaming`, or `error` status
- readable error text
- active AbortController/request identity
- `sendMessage()`, `stopGeneration()`, and `newChat()`

Sending adds a local user message and an empty streaming assistant message. Each `delta` appends text. `done` replaces temporary IDs/content with canonical backend response data. `error` preserves visible content and marks the assistant turn failed. Stop aborts the request, preserves partial content, marks it stopped, and ignores late callbacks.

## Frontend UI

The first screen is the usable Chat workspace:

- narrow left rail with product name, New Chat command, API health, and API base URL
- compact header with the configured provider/model and stream status
- central message list with quiet user/assistant differentiation
- compact empty state when no messages exist
- bottom composer with multiline input and Send/Stop icon buttons
- responsive single-column mobile layout

The configured provider/model come from `VITE_DEFAULT_PROVIDER` and `VITE_DEFAULT_MODEL`, with safe example defaults. Dynamic model selection and conversation navigation remain in `P1-M3-S7`.

UI uses Lucide icons with accessible labels/tooltips. It does not introduce decorative marketing sections, nested cards, gradients, or fake history.

## Dependencies

- `zustand`: required by `P1-M3-S5` for focused, testable Chat state
- `lucide-react`: familiar command icons required by the UI conventions

No Markdown, syntax-highlighting, component-system, or additional testing dependency is added.

## Test Design

Backend tests cover successful deltas/done persistence, existing history, Provider failure rollback, cancellation rollback, SSE headers/framing, and terminal error events.

Frontend tests cover SSE frames split across network chunks, done/error handling, AbortSignal behavior, Zustand success/error/stop transitions, and stale callback suppression.

Browser verification starts Vite and uses Playwright route interception for health and streaming API responses. It verifies empty, streaming, completed, error, and stopped states without real credentials or paid APIs. Desktop and mobile screenshots are inspected for overflow, overlap, and readable framing.

## Review Cadence

This batch receives Codex self-review only. The next consolidated Fable 5 review remains after M4.

## Deferred Work

- conversation sidebar data and history recovery
- dynamic Models API and selector
- Markdown rendering
- token/cost/latency persistence
- detailed error envelope, logging, and retries
- Tool Calling and all later-plan capabilities
