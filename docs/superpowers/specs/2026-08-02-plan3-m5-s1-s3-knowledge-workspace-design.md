# Plan 3 M5 S1～S3 Knowledge Workspace Design

## Status And Scope

This design implements only `P3-M5-S1～S3`:

- add strict frontend Knowledge Base and Document response types;
- add list, create, and multipart upload API wrappers;
- add a third Knowledge workspace that lists and creates Knowledge Bases;
- upload one `.md`, `.txt`, or `.pdf` document to the selected Knowledge Base;
- display the final parse, chunk, and embedding lifecycle returned by that upload;
- update current documentation and acceptance evidence.

The user explicitly started this batch and the repository Plan 3 documents are
the authoritative approved product design. This file records the bounded UI
adaptation before implementation. It does not start `P3-M5-S4～S6`, add a RAG
frontend store or chat, display retrieval sources, add backend routes, or
implement any Plan 4+ capability. The normal `main` workspace remains unstaged
and uncommitted for the user's manual Git workflow.

## Acceptance Matrix

| Requirement | Current evidence | Gap | Minimal S1～S3 change |
|---|---|---|---|
| Typed Knowledge API | Backend exposes strict `KnowledgeBaseRead` and `DocumentRead` schemas | Frontend has no matching types or wrapper | Add `types/knowledge.ts` and tested list/create/upload functions |
| View Knowledge Bases | `GET /knowledge-bases` returns newest-first rows | No Knowledge workspace | Add loading, empty, error, and ready list states |
| Create Knowledge Base | `POST /knowledge-bases` accepts a name plus optional metadata | No creation flow | Add bounded name/description form, busy state, safe error, and select the created row |
| Upload Document | Nested multipart POST accepts one `file` field | No upload UI | Add a selected-KB file form for `.md`, `.txt`, and `.pdf` |
| Display ingestion state | Upload synchronously returns final parse/chunk/embedding statuses, including safe processing failure resources | No status view | Render all three statuses, safe error text, Document ID, filename, type, size, and timestamp |
| Async safety | Existing pages guard initial effects and disable conflicting work | New page has no request ownership | Guard unmounts, serialize create/upload, and clear upload state on KB change |
| Plan boundary | Backend explicitly has no Document list/detail/chunk-query routes | Detailed Plan prose mentions future Document list and Chunk preview | Do not fabricate these views or add backend APIs; document the limitation |

## Alternatives Considered

### 1. Feature-Local State With Small Components — Chosen

`KnowledgeBasePage` owns the API lifecycle while focused components render the
list, creation form, upload form, and returned Document state. This matches the
existing page architecture, keeps async ownership visible, and gives S4～S6 a
clean integration point without creating its state early.

### 2. A Shared Zustand Knowledge Store

A shared store could later serve RAG Chat, but S1～S3 have one page and no
cross-page Knowledge state requirement. Defining future RAG actions now would
cross the current batch and make the API contract harder to change.

### 3. One Monolithic Page Component

This would minimize file count, but list/create/upload/error states would be
tightly coupled and harder to test independently. It also conflicts with the
Plan's named component deliverables.

## Chosen Architecture

### 1. Typed API Boundary

Create `frontend/src/types/knowledge.ts` with literal unions matching the
backend lifecycle schemas:

- `DocumentFileType`: `md | txt | pdf`;
- parse status: `uploaded | parsing | parsed | failed`;
- chunk status: `pending | chunking | chunked | failed`;
- embedding status: `pending | embedding | ready | failed`;
- `KnowledgeBaseCreate`, `KnowledgeBase`, and `KnowledgeDocument` response
  types. The prefixed Document name avoids colliding with the DOM `Document`.

Create `frontend/src/api/knowledge.ts` with:

- `fetchKnowledgeBases()` using the plural list route;
- `createKnowledgeBase(request)` using JSON POST;
- `uploadKnowledgeDocument(knowledgeBaseId, file)` using `FormData` with one
  `file` part.

The upload wrapper must not set `Content-Type`; the browser owns the multipart
boundary. Knowledge Base IDs are path-encoded. Non-success responses use the
existing structured safe-error reader, and transport/invalid-JSON failures use
fixed frontend messages rather than response bodies.

### 2. Third Workspace Navigation

Extend `WorkspaceView` to `chat | agent | knowledge`. `readWorkspace` recognizes
only these explicit values and still defaults unknown values to Chat.
`buildWorkspaceUrl` continues preserving unrelated query and hash state. App
renders `KnowledgeBasePage` only for the new value.

The shared sidebar gains a third button and a small Knowledge-specific note. It
does not place the Knowledge Base list in the global sidebar because the list,
creation form, and upload state belong to one feature page and need more room on
small screens.

### 3. Knowledge Base List And Creation

The page content uses a quiet two-column engineering layout:

- a compact left panel for create form and Knowledge Base list;
- a flexible right panel for the selected Knowledge Base and document upload.

Initial list state is loading. On success, the first row is selected; an empty
response shows an explicit empty state. List errors expose a retry action.
Creation trims the name, sends an optional trimmed description, disables
duplicate submission, inserts/reloads the created row, and selects it. A create
failure preserves the user's input and renders only the safe API message.

There is deliberately no update or delete UI in this batch because S2 requires
create and view only.

### 4. Upload And Status Flow

`FileUploadPanel` is disabled until a Knowledge Base is selected. It accepts
case-insensitive `.md`, `.txt`, and `.pdf` filenames and gives immediate
client-side feedback for a missing or unsupported file, while the backend
remains authoritative for content, size, duplicate, and processing limits.

The submit flow captures the selected Knowledge Base, disables list/create/
upload conflicts, and displays a bounded uploading state. A successful HTTP
201 is always treated as a Knowledge Document resource, even when one lifecycle field is
`failed`. `DocumentStatusCard` renders:

- original filename, file type, byte size, Document UUID, and created time;
- Parse, Chunk, and Embedding badges with the exact returned states;
- the safe `error_message` when present.

It does not render `file_path`, `file_hash`, raw metadata, or internal Provider
diagnostics. Selecting a different Knowledge Base clears the prior result so a
Document is never displayed under the wrong owner.

### 5. Async And Error Boundaries

Initial health/list effects ignore results after unmount. Create and upload are
serialized by their busy states. Handler completions verify request ownership
before changing visible state, so leaving the page or changing owner cannot
apply a stale response. Safe API errors are readable in `role=alert` regions;
loading announcements use `role=status`.

No polling is added: the current backend upload contract is synchronous and
returns its final lifecycle state. Polling would imply a status endpoint that
does not exist.

## Testing Strategy

TDD proceeds in three vertical slices:

1. API tests fail before the typed wrapper exists, then verify URLs, JSON body,
   `FormData`, absent manual multipart header, safe backend errors, transport
   errors, and invalid success JSON.
2. workspace/page tests fail before navigation and list/create exist, then cover
   URL selection, loading, empty, retry, successful create/selection, and safe
   creation failure.
3. mounted DOM tests fail before upload/status exists, then cover supported and
   unsupported files, exact Knowledge Base ownership, busy behavior, successful
   lifecycle rendering, HTTP error rendering, and clearing state on KB change.

After focused GREEN, run the full frontend test suite, TypeScript check, and
production build. A real-browser smoke uses local mocked API responses so it
does not read the user database, use credentials, or call a paid Provider.
Backend full regression is read-only with respect to the protected user
database and uses the repository test fixtures.

## Documentation And Explicit Limitations

Update README, README_CN, CHANGELOG, architecture, Knowledge Base design, and
the active execution table with exact verification evidence. State clearly that
this batch can show the current upload response only. Persistent Document
listing, detail, Chunk preview, retry, and deletion remain unavailable because
their backend query/lifecycle APIs do not exist. RAG Chat and source cards remain
`P3-M5-S4～S6`.
