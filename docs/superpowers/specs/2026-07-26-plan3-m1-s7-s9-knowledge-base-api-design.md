# Plan 3 M1 S7～S9 Knowledge Base API Design

**Date:** 2026-07-26

**Status:** Ready for user review

## Goal

Complete Plan 3 Milestone 1 by adding a service-owned Knowledge Base CRUD
boundary, a thin FastAPI API, focused schema/service/API tests, and the formal
M1 data-model document.

This batch is limited to `P3-M1-S7～S9`. It does not add Document APIs, upload
storage, parsers, Chunking, Embedding, a Qdrant client, retrieval, RAG answer
generation, frontend behavior, or any later-Plan capability.

## Baseline

- `main` is clean at `13e0cba4313580195da3e26c9ab1240a68d1dcfb`.
- `HEAD == origin/main`.
- The latest commit is `feat(knowledge): add plan 3 persistence models`.
- Alembic head is `20260726_0005`.
- `KnowledgeBase`, `Document`, `DocumentChunk`, and `RagQuery` ORM/create/read
  schema contracts are implemented and verified.
- SQLite remains the primary business and audit database.
- Qdrant remains a separate vector store. This batch neither connects to it nor
  claims collection-deletion behavior.
- Existing request-scoped database dependencies own commit and rollback;
  services mutate and flush without committing.
- Root `AGENTS.md` overrides legacy Claude review text. Codex self-review is the
  only M1 review gate.

## Acceptance Matrix

| Step | Acceptance requirement | Current evidence | Gap | Minimal delivery |
|---|---|---|---|---|
| `P3-M1-S7` | Create, list, detail, update, and delete service behaviors pass | Stable SQLAlchemy session/service patterns and the four Plan 3 models exist | No Knowledge Base update schema, service, domain error, or service tests | Add `KnowledgeBaseUpdate`, `KnowledgeBaseService`, `KnowledgeBaseNotFoundError`, exports, and focused tests |
| `P3-M1-S8` | CRUD API tests pass and OpenAPI exposes the routes | FastAPI dependency injection, unified safe errors, request-scoped transactions, and thin-route patterns exist | No service dependency, router, main-app registration, error mapping, or API tests | Add plural `/knowledge-bases` routes, safe 404 mapping, OpenAPI/API tests, and rollback coverage |
| `P3-M1-S9` | M1 review and data-model documentation are complete | S1～S6 acceptance evidence and current architecture docs exist | No formal `docs/20-knowledge-base-design.md`; current truth ends at S6 | Document the four tables, statuses, integrity rules, CRUD contract, boundaries, verification, and Codex review |

## Considered Approaches

### 1. Thin route plus domain service — selected

Use:

```text
FastAPI route
-> Pydantic schema validation
-> KnowledgeBaseService
-> SQLAlchemy Session
-> KnowledgeBaseRead
```

This follows the existing Conversation and Agent service boundaries. The
service is independently testable, the route owns only HTTP concerns, and the
request-scoped database dependency keeps transaction behavior consistent.

### 2. Add a Repository abstraction — rejected

A Repository interface would add another layer without a second persistence
implementation or a current portability need. SQLAlchemy and Alembic already
preserve reasonable portability, and SQLite remains the long-term primary
database.

### 3. Query SQLAlchemy directly from routes — rejected

This reduces the initial file count but violates the repository rule that
business logic belongs in services. It would also duplicate lookup/update/
delete behavior and make error-path testing harder.

## File And Ownership Boundaries

Schemas and services:

- `backend/app/schemas/knowledge_base.py`: add the partial
  `KnowledgeBaseUpdate` contract.
- `backend/app/schemas/__init__.py`: export `KnowledgeBaseUpdate`.
- `backend/app/services/knowledge_base_service.py`: own CRUD lookup, ordering,
  partial-update application, timestamp changes, deletion, and flush behavior.
- `backend/app/services/errors.py`: add `KnowledgeBaseNotFoundError`.
- `backend/app/services/__init__.py`: export the service and error.

HTTP:

- `backend/app/api/dependencies.py`: construct a request-scoped
  `KnowledgeBaseService`.
- `backend/app/api/errors.py`: map the domain not-found error to a safe 404.
- `backend/app/api/v1/knowledge_bases.py`: expose the five CRUD routes.
- `backend/app/main.py`: register the router below `/api/v1`.

Tests:

- `backend/tests/test_knowledge_schemas.py`: extend the existing schema suite
  with partial-update validation.
- `backend/tests/test_knowledge_base_service.py`: service state and domain-error
  tests using a new temporary SQLite database.
- `backend/tests/test_knowledge_base_api.py`: OpenAPI, CRUD, validation, safe
  error, and transaction tests using a new temporary SQLite database.

Documentation:

- `docs/20-knowledge-base-design.md`: formal M1 model/API/boundary reference.
- `docs/00-project-overview.md`: current completed scope and next batch.
- `docs/01-architecture.md`: current service/API data flow.
- `README.md`, `README_CN.md`, and `CHANGELOG.md`: current completed scope.
- `docs-plan/03-PLAN3/03-PLAN3-执行步骤表 (V1.0).md`: Batch 3 evidence and M1
  acceptance state.
- an implementation plan under `docs/superpowers/plans/`.

No migration, model column, upload, Document API, RAG pipeline, Provider,
Qdrant client, Tool, or frontend file is created.

## Schema Design

Add:

```python
class KnowledgeBaseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: KnowledgeBaseName | None = None
    description: str | None = None
    embedding_provider: OptionalProviderName | None = None
    embedding_model: OptionalModelName | None = None
    vector_store: OptionalProviderName | None = None
    vector_collection_name: OptionalModelName | None = None
```

An after-validator enforces:

1. at least one field must be present in `model_fields_set`;
2. `name` cannot be `null` when explicitly supplied;
3. `vector_store` cannot be `null` when explicitly supplied.

The distinction between omitted and explicit `null` is intentional:

- omitted fields remain unchanged;
- `description`, `embedding_provider`, `embedding_model`, and
  `vector_collection_name` may be cleared with explicit `null`;
- `name` and `vector_store` remain required persisted values.

`KnowledgeBaseCreate` and `KnowledgeBaseRead` keep their existing field set.
No Document, Chunk, or RagQuery schema changes are needed.

## Service Design

`KnowledgeBaseService` receives one SQLAlchemy `Session`.

### Create

```python
def create_knowledge_base(
    self,
    data: KnowledgeBaseCreate,
) -> KnowledgeBase
```

Construct a `KnowledgeBase` from `data.model_dump()`, add it, flush it, and
return the ORM row. Do not commit.

### List

```python
def list_knowledge_bases(self) -> list[KnowledgeBase]
```

Use deterministic order:

```text
created_at DESC
id ASC
```

No pagination, filtering, search, counts, document expansion, or Qdrant state
is included in M1.

### Detail

```python
def get_knowledge_base(
    self,
    knowledge_base_id: UUID,
) -> KnowledgeBase
```

Load by primary key. Missing rows raise
`KnowledgeBaseNotFoundError(knowledge_base_id)`.

### Update

```python
def update_knowledge_base(
    self,
    knowledge_base_id: UUID,
    data: KnowledgeBaseUpdate,
) -> KnowledgeBase
```

Resolve the row through `get_knowledge_base()`. Apply only keys from
`data.model_dump(exclude_unset=True)`. Set `updated_at` from `utc_now`; if the
new value is not greater than the existing value, advance by one microsecond,
matching the existing deterministic Conversation timestamp policy. Flush and
return the row. Do not commit.

### Delete

```python
def delete_knowledge_base(
    self,
    knowledge_base_id: UUID,
) -> None
```

Resolve the row, delete it, and flush. Existing ORM/database cascades remove
owned Documents, DocumentChunks, and RagQueries. Because no Qdrant client or
collection exists in this batch, deletion has no vector-store side effect and
the API documentation states that limitation explicitly.

## HTTP Contract

All paths use the plural kebab-case prefix `/api/v1/knowledge-bases`.

| Method | Path | Success | Response |
|---|---|---:|---|
| `POST` | `/api/v1/knowledge-bases` | 201 | `KnowledgeBaseRead` |
| `GET` | `/api/v1/knowledge-bases` | 200 | `list[KnowledgeBaseRead]` |
| `GET` | `/api/v1/knowledge-bases/{knowledge_base_id}` | 200 | `KnowledgeBaseRead` |
| `PATCH` | `/api/v1/knowledge-bases/{knowledge_base_id}` | 200 | `KnowledgeBaseRead` |
| `DELETE` | `/api/v1/knowledge-bases/{knowledge_base_id}` | 204 | empty body |

Routes validate ORM rows through `KnowledgeBaseRead.model_validate`. They do
not contain SQLAlchemy queries, update loops, transaction control, or business
error translation.

The original Plan 3 API list omitted update, but the active execution table
explicitly requires update behavior in S7. The user approved the `PATCH`
contract on 2026-07-26.

## Error And Transaction Behavior

Add:

```python
class KnowledgeBaseNotFoundError(ServiceError):
    def __init__(self, knowledge_base_id: UUID) -> None:
        super().__init__(f"Knowledge base not found: {knowledge_base_id}")
        self.knowledge_base_id = knowledge_base_id
```

The unified HTTP mapping is:

```text
status: 404
code: knowledge_base_not_found
message: Knowledge base not found
```

The HTTP response never includes the requested UUID, SQL text, database path,
field values, document metadata, or exception text.

Other behavior remains shared:

- malformed UUIDs, empty PATCH bodies, invalid fields, blank required strings,
  and explicit null for non-nullable update fields return the unified 422
  validation envelope;
- SQLAlchemy failures return the fixed 503 database envelope;
- unexpected failures return the fixed 500 envelope;
- `get_db_session` commits only after the route returns successfully and rolls
  back any exception;
- a commit failure cannot return a successful 201, 200, or 204 response.

## Test Strategy

All tests use newly created temporary SQLite databases and synthetic values.
They do not access `backend/ai_agent_lab.db`, Qdrant, real Providers, real
credentials, local `.env` files, or network Tools.

### Schema/service RED-GREEN cycle

Start with failing imports/behavior for:

- partial update schema acceptance;
- omitted versus explicit-null semantics;
- empty update rejection;
- explicit null rejection for `name` and `vector_store`;
- create and detail;
- deterministic list ordering;
- partial update and monotonic `updated_at`;
- nullable-field clearing;
- delete behavior;
- safe not-found behavior for detail, update, and delete.

Minimal production implementation follows only after the tests fail for the
expected missing feature.

### API RED-GREEN cycle

Start with failing tests for:

- all five paths/methods appearing in OpenAPI;
- create/list/detail/update/delete status and response bodies;
- 204 deletion with an empty body;
- deterministic list response order;
- safe 404 for an unknown UUID;
- 422 for malformed UUID, empty PATCH, unknown fields, blank names, and invalid
  null values;
- no persistence for invalid requests;
- rollback and safe 503 when request-scoped commit fails.

Then add the service dependency, error mapping, router, and main-app
registration needed to make those tests pass.

### Matching and full verification

After GREEN:

1. run the Knowledge Base schema/service/API/model/migration focused suite;
2. run the complete backend test suite and `pip check`;
3. run frontend test, typecheck, and production build regressions;
4. run `upgrade head`, `current --check-heads`, and `alembic check` against a
   new system-temporary SQLite database, then remove that verified temp root;
5. scan Markdown links/images, added-line high-confidence secrets, real
   Provider hosts, generated database artifacts, `web_fetch` runtime,
   later-Plan runtime, and out-of-batch paths;
6. require `git diff --check` success, zero staged paths, and unchanged
   `HEAD == origin/main == 13e0cba4313580195da3e26c9ab1240a68d1dcfb`.

## S9 Documentation And Review

`docs/20-knowledge-base-design.md` records:

- why SQLite stores business/audit metadata while Qdrant is reserved for later
  vector storage;
- the four M1 table purposes and ownership graph;
- KnowledgeBase fields and CRUD mutability;
- Document parse/chunk/embedding statuses;
- DocumentChunk order/count/page/source/vector bridge fields;
- RagQuery query/source/answer-message bridge fields;
- named checks, composite ownership constraints, and cascade behavior;
- all five Knowledge Base API operations and safe error envelopes;
- explicit M2+ and Plan 4+ deferrals.

The active execution table receives a dated S7～S9 acceptance record. The
Codex self-review classifies every finding as:

- must fix;
- later Step;
- accepted limitation;
- not applicable.

Legacy Claude/Fable review text is not executed. No release tag or Plan 3
completion claim is made because only Milestone 1 is ending.

## Explicit Non-Goals

- Document CRUD or upload API;
- multipart handling or upload directories;
- Markdown, TXT, or PDF parsing;
- cleaning or Chunking;
- Embedding providers or model calls;
- Qdrant client, collection creation/deletion, upsert, search, or payloads;
- ingestion pipelines or background tasks;
- Retriever, RAG prompt, answer generation, RagQuery API, or Tool registration;
- frontend Knowledge Base pages, API wrappers, types, or screenshots;
- pagination, search, filtering, counts, bulk operations, or soft deletion;
- authentication, multi-user ownership, or PostgreSQL infrastructure;
- Advanced RAG, Hybrid Search, Rerank, Evaluation, Trace runtime, Memory, OCR,
  multimodal, MCP, Human Approval, or later-Plan capabilities;
- branch changes, staging, commits, pushes, tags, or external review.
