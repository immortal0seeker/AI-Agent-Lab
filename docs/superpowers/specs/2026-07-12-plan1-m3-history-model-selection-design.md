# Plan 1 M3 Model Selection And Conversation Recovery Design

## Scope

This design covers only `P1-M3-S7` through `P1-M3-S9`:

- expose Registry models through a read-only API
- list persisted conversations by recent activity
- return ordered messages for one conversation
- select a provider/model in the frontend
- select and restore persisted conversations
- recover the selected conversation through a URL query parameter
- complete M3 backend, frontend, and browser verification

Conversation deletion, manual rename, pagination, search, Markdown rendering,
token/cost/latency persistence, logging, detailed M4 error envelopes, Tool
Calling, RAG, Memory, MCP, Voice, Vision, and Desktop behavior are outside this
batch.

## Architecture Choice

The implementation uses independent resource APIs and one Chat workspace
store. Models, conversations, and messages remain separate backend resources,
while the existing Zustand Chat store coordinates the frontend workflow.

This keeps the route boundary thin:

```text
Route -> schema validation -> service or Registry -> response schema
```

No composite workspace bootstrap endpoint or additional frontend state library
is introduced.

## Backend APIs

The backend adds these read-only routes:

```text
GET /api/v1/models
GET /api/v1/conversations
GET /api/v1/conversations/{conversation_id}/messages
```

`GET /models` returns Registry entries in configured order. Each response item
contains provider, model, display name, streaming/tools/JSON capability labels,
and optional input/output prices. The endpoint does not initialize a Provider
or expose credentials.

`GET /conversations` returns all conversations ordered by `updated_at DESC`,
then `id` for deterministic ties. Plan 1 uses a local, primarily single-user
SQLite database, so pagination and search are deferred until real data volume
requires them.

`GET /conversations/{id}/messages` returns messages ordered by `created_at`,
then `id`, using the existing Conversation Service ordering guarantee. An
unknown conversation uses the existing readable 404 mapping.

No database field or Alembic migration is required.

## Conversation Metadata Semantics

When Chat creates a conversation, its title comes from the first user message:

1. trim leading and trailing whitespace
2. collapse internal whitespace runs to one space
3. keep at most the first 50 characters
4. fall back to `New conversation` only if normalized content is empty, although
   request validation normally prevents that case

After every successful non-streaming or streaming completion, Chat records the
request provider/model as the conversation defaults and advances
`updated_at`. This makes the list order reflect recent successful activity and
lets refresh recovery restore the last successfully used model.

Metadata changes follow the same transaction as the turn. Provider failure,
empty stream, commit failure, or client cancellation must not persist a new
title, selected model, activity timestamp, user message, assistant message, or
LLM call.

## Frontend API And Types

Focused frontend modules own the resource contracts:

- `src/types/models.ts`: Registry model response type
- `src/types/conversations.ts`: conversation and persisted message types
- `src/api/models.ts`: `fetchModels()`
- `src/api/conversations.ts`: `fetchConversations()` and
  `fetchConversationMessages()`
- `src/utils/conversationUrl.ts`: read and update the `conversation` query
  parameter without adding a router dependency

API wrappers use the existing base URL and shared JSON request behavior. They
surface readable HTTP failures and do not contain UI state.

## Zustand Workspace State

The existing Chat store expands to own:

- Registry model options
- persisted conversation summaries
- selected provider/model
- selected conversation ID and messages
- initialization and conversation-loading state
- readable workspace errors
- existing streaming request identity and AbortController state

The store receives injectable API functions in tests. Production defaults use
the real frontend wrappers.

Initialization accepts the conversation ID read from the URL, loads models and
conversations in parallel, selects the configured environment default when it
exists (otherwise the first Registry model), and loads the requested
conversation when it appears in the list. A missing or stale URL ID leaves a
new empty Chat and is removed from the URL by the page synchronization effect.

Selecting a conversation loads its messages before replacing the visible
message list. The conversation's saved provider/model becomes selected when it
still exists in the Registry. A request identity prevents an older history
response from replacing a newer selection.

Selecting a model changes only the next request until a successful Chat turn
persists it as the conversation default. Model and conversation controls are
disabled during streaming. New Chat may abort streaming, clears the selected
conversation and messages, removes the URL parameter, and retains the current
model selection.

After a successful stream, the store reloads conversation summaries so a new
automatic title and activity order become visible. Reload failure does not
invalidate the already completed Chat response; it surfaces a workspace error
that can be retried by reinitialization or refresh.

## URL Recovery

`ChatPage` reads `?conversation=<uuid>` on initial mount and passes it to store
initialization. It subscribes to selected conversation changes and uses
`history.replaceState` to add or remove the query parameter without navigation.

The helper preserves unrelated query parameters and the URL hash. Invalid UUID
text is treated as no selected conversation and is removed after
initialization. The backend remains authoritative: the URL stores only an ID,
never message content or model credentials.

## User Interface

The existing quiet engineering-workspace layout is extended rather than
replaced:

- the sidebar shows New Chat followed by a compact conversation list
- conversations show title and recent update time, with a clear selected state
- the header replaces static model text with a native select control
- loading and empty states occupy stable dimensions and do not shift the shell
- failures appear as readable inline status without hiding existing messages
- mobile keeps the compact top rail and exposes conversation navigation through
  a small drawer or collapsible panel using the existing layout, without adding
  a component framework

The model selector displays `display_name` and keeps provider/model identity in
the option value. It is disabled while initializing, when no models exist, or
while a stream is active.

Manual rename, delete, search, model capability editing, Markdown rendering,
and fake conversation seed data are not added.

## Error And Race Handling

- Models or initial conversation list failures produce a workspace error and a
  usable New Chat shell, but sending remains disabled until a model exists.
- Message-history 404 or network failure leaves the previously visible
  conversation unchanged.
- Older history requests cannot overwrite a newer selected conversation.
- New Chat and unmount cleanup prevent late stream/history callbacks from
  restoring cleared state.
- A failed or cancelled Chat turn remains local according to the Batch 8
  successful-completion-only persistence rule.
- Provider errors remain readable and do not expose API keys.

## Test Design

Backend service tests cover deterministic recent-activity ordering, ordered
message retrieval, automatic first-message titles, successful default-model and
timestamp updates, and rollback behavior.

Backend API tests cover Models, Conversation List, Message List, OpenAPI route
visibility, response schemas, deterministic order, and unknown conversation
404 behavior.

Frontend API tests cover typed resource responses and HTTP errors. Store tests
cover initialization, environment fallback, model switching, conversation
selection, persisted message mapping, successful list refresh, stale response
suppression, and New Chat reset behavior. URL helper tests cover add, replace,
remove, unrelated query preservation, and invalid IDs.

Browser verification uses route interception and sanitized mock data to verify:

- model options load and can be changed
- conversations load and can be selected
- messages appear in persisted order
- the URL records the selected conversation
- page refresh restores that conversation
- New Chat clears the URL and messages
- desktop and mobile layouts have no overflow or overlap

No real Provider, credential, paid API, or repository `.env` file is used.

## Documentation And Review

README, README_CN, project overview, architecture, Provider documentation, and
the Plan 1 execution table will describe the completed M3 workflow without
claiming Markdown, deletion, M4 observability, or real Provider verification.

This batch receives Codex self-review only. Per the agreed cadence, the next
concentrated Fable 5 or Claude Code review occurs after M4.

## Deferred Work

- conversation rename and deletion
- pagination and conversation search
- Markdown and code-block rendering
- token, cost, and latency persistence
- detailed errors, retries, and logging
- Tool Calling and every later-plan capability
