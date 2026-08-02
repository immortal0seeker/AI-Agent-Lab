# Plan 3 M5 S4～S6 RAG Chat Workspace Design

## Status And Scope

This design implements only `P3-M5-S4～S6`:

- add strict frontend types and API wrappers for retrieval-only RAG Query and
  non-streaming RAG Chat;
- add a focused Zustand store for the RAG workspace lifecycle;
- add a RAG Chat view inside the existing Knowledge workspace;
- create a dedicated Conversation on the first question, select a registered
  model, and ask against the selected Knowledge Base;
- display the grounded answer, exact returned sources, retrieval metadata, and
  traceable RAG/LLM/Conversation IDs;
- update current documentation and verification evidence.

The user's explicit start instruction approves the repository Plan 3 product
scope. This file records the bounded frontend adaptation before implementation.
It does not add backend routes, streaming, RagQuery read/history APIs, Advanced
RAG, hybrid search, reranking, evaluation, Trace runtime, memory, OCR, or
multimodal behavior. Work stays on the normal `main` workspace and remains for
the user's manual Git workflow.

## Acceptance Matrix

| Requirement | Current evidence | Gap | Minimal S4～S6 change |
|---|---|---|---|
| Typed RAG API | Backend exposes strict `/rag/query` and `/rag/chat` schemas | Frontend has no matching contract | Add `types/rag.ts` and tested Query/Chat POST wrappers |
| RAG state | Existing Chat has a global Zustand pattern | No isolated non-streaming RAG lifecycle | Add a small store for model initialization, dedicated conversation, turns, busy/error state, and request ownership |
| Ask by Knowledge Base | Knowledge workspace already owns list/create/selection | No RAG view | Add Documents/RAG Chat tabs and pass the selected Knowledge Base to `RagChatPage` |
| Existing Conversation requirement | Backend RAG Chat requires a non-null Conversation UUID | The frontend cannot currently create one directly | Add the missing typed Conversation create wrapper and create one on the first RAG question |
| Answer display | RAG Chat returns persisted messages and answer | No answer panel | Show the user question, answer, resolved model, and traceable IDs |
| Source display | Each source has stable index, document/chunk IDs, content, score, heading/page and JSON metadata | No source UI | Add a source list/card with exact order, safe text rendering, score, provenance, and bounded metadata formatting |
| Async safety | Backend call is non-streaming and can fail | No stale response protection | Serialize sends, preserve failed drafts, ignore superseded results, and reject mismatched KB/conversation/source ownership |
| Persistence boundary | Messages and RagQuery are persisted, but no frontend RagQuery/history read API exists | Sources cannot be restored after reload | Keep current-session RAG turns only and document the limitation |

## Alternatives Considered

### 1. Knowledge Workspace With Documents / RAG Chat Tabs — Chosen

`KnowledgeBasePage` continues to own Knowledge Base selection and document
management. A local tab switches the selected Knowledge Base detail between the
existing document flow and a focused `RagChatPage`. This preserves the quiet
three-item global navigation, avoids a second Knowledge Base loader, and makes
owner changes explicit to the RAG store.

### 2. A Fourth Global RAG Workspace

This gives RAG a full page but crowds the global sidebar and duplicates
Knowledge Base selection/loading. It also makes it easier for the document and
RAG views to disagree about the active owner.

### 3. Append Chat Below Document Upload

This minimizes navigation code but creates one long, coupled detail surface and
makes document-upload and RAG request states compete visually. The Plan names a
separate `RagChatPage`, so a bounded tab is clearer.

## Chosen Architecture

### 1. Typed API Boundary

Create `frontend/src/types/rag.ts` with the exact backend request/response
contracts:

- `RagRetrievalRequest`, `RagQueryResponse`, and retrieval metadata;
- `RagChatRequest`, `RagChatResponse`, and answer metadata;
- `RagSource` with source index, Knowledge Base/Document/Chunk IDs, filename,
  chunk index/content/score, heading/page, and JSON metadata;
- `RagTurn` as the UI-owned current-session answer record.

Create `frontend/src/api/rag.ts` with `queryKnowledgeBase()` and
`createRagChat()`. Both use JSON POST, the shared URL/error helpers, a fixed
transport message, and a fixed invalid-success-JSON message. The Chat wrapper
accepts an optional `AbortSignal` for page/store lifecycle cancellation without
claiming backend generation cancellation.

Extend the existing Conversation API with `createConversation(request)`. This
is an already implemented backend capability required to satisfy the RAG Chat
contract; no backend behavior changes.

### 2. Focused RAG Store

Create `frontend/src/stores/ragStore.ts`. It owns:

- model loading and configured-model fallback;
- selected Knowledge Base, provider, and model;
- a current dedicated Conversation UUID;
- current-session `RagTurn` records;
- workspace and request loading/error states;
- request IDs and an AbortController for stale-result protection.

The store does not duplicate the Knowledge Base list. `setKnowledgeBase(id)` is
called by `RagChatPage`; changing the owner aborts/invalidates the active client
request, clears the prior conversation and turns, and prevents sources from one
Knowledge Base appearing under another.

On the first successful submit attempt for a session, the store creates a
Conversation using the selected provider/model and a bounded title derived from
the selected Knowledge Base name, not the private question. It then calls
`/rag/chat`. Later questions reuse that Conversation
so the backend can include RAG history. `newChat()` clears only the current RAG
Conversation/turns and preserves Knowledge Base/model selection.

Before displaying a response, the store checks:

- response Conversation ID equals the requested dedicated Conversation;
- metadata Knowledge Base ID equals the selected/requested owner;
- every source has the same Knowledge Base ID;
- source indices are contiguous and one-based;
- `used_source_count` equals the returned source count.

Inconsistent responses fail closed with a fixed frontend message. Raw response
bodies, queries, sources, Provider diagnostics, and credentials are not logged.

### 3. Page And Component Boundaries

`KnowledgeBasePage` gains local `documents | rag` tabs. Knowledge Base creation,
selection, upload, and status remain owned by the existing page. Switching a
Knowledge Base clears both owner-specific upload output and RAG session state.

`RagChatPage` consumes one selected `KnowledgeBase`, initializes the RAG store,
and renders:

- selected Knowledge Base identity;
- a registered-model selector;
- New RAG chat action and current Conversation ID when present;
- loading/error/empty/result states;
- a non-streaming composer that clears only after a successful turn;
- current-session user question and grounded answer panels.

`RagAnswerPanel` renders answer text and audit metadata. It delegates sources to
`SourceCitationList`, which renders `RagSourceCard` entries in backend order.
Source content and answer text use React text nodes, not HTML or Markdown
injection.

### 4. Source Presentation

Each source card displays:

- `[source_index] filename`;
- similarity score;
- chunk content;
- heading and/or page when present;
- document ID, chunk ID, and chunk index;
- JSON-safe metadata entries.

Metadata values are formatted deterministically and bounded for display. The UI
does not infer citations that the backend did not return, reorder sources, or
perform client-side reranking. An empty source array has an explicit
"No sources were used" state while still showing the backend answer.

### 5. Error And Async States

Model initialization exposes loading/error/retry. The composer is disabled
without a selected Knowledge Base/model or while a request is active. A failed
Conversation create or RAG call preserves the question draft and renders only
the safe API message. A successful response appends exactly one turn.

Selecting another Knowledge Base or starting a new RAG chat invalidates the
active request before clearing state. A late response therefore cannot restore
old-owner content. Client abort is lifecycle control only; documentation does
not claim that the backend Provider call was cancelled.

## Testing Strategy

TDD proceeds in three vertical slices:

1. S4 API/types/store RED verifies both endpoints, complete JSON shapes,
   structured safe errors, transport/invalid JSON, model fallback, first-turn
   Conversation creation, owner validation, failure preservation, and stale
   response suppression.
2. S5 page RED verifies Documents/RAG tabs, selected Knowledge Base/model,
   loading/error/empty states, successful question flow, New RAG chat, and
   conflicting-control disabling.
3. S6 component RED verifies ordered sources, filename/content/score,
   heading/page, IDs, metadata, zero-source state, audit IDs, and absence of raw
   HTML execution.

After focused GREEN, run the complete frontend suite, TypeScript check, and
production build. A real-browser smoke intercepts local API responses and uses
only synthetic Knowledge Base, model, Conversation, answer, source, and health
data. Backend regression uses test fixtures from a system temporary working
directory and never reads the protected user database.

## Documentation And Explicit Limitations

Update README, README_CN, CHANGELOG, Architecture, Knowledge Base Design, Naive
RAG, and the active Plan 3 execution table. Current-session RAG answers and
sources are visible, but a reload cannot reconstruct source cards because no
RagQuery list/detail endpoint exists. RAG remains non-streaming. The dedicated
Agent knowledge Tool still has no frontend, and all Advanced RAG/Plan 4+
capabilities remain deferred.
