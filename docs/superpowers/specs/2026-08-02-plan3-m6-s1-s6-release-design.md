# Plan 3 M6 S1～S6 Test And Release Closure Design

## Status And Scope

This design closes only `P3-M6-S1～S6` in two consecutive repository-sized
batches: S1～S3 test evidence first, then S4～S6 RAG/Demo/release closure. The
user's explicit execution instruction approves the existing Plan 3 product
scope and requires Codex self-review only. No Claude Code or other external
review is requested, run, or treated as a gate.

M6 does not introduce a new RAG strategy or expand the runtime. It verifies the
implemented Knowledge Base, Document ingestion, Embedding, VectorStore,
Retriever, RAG Query/Chat, Tool, and frontend contracts; adds durable sanitized
Demo evidence; synchronizes release metadata and documentation; and prepares
the repository for the user's manual `v0.3.0` commit/tag workflow.

The work does not add Document history/delete APIs, streaming RAG, Advanced
RAG, hybrid search, reranking, evaluation, Trace runtime, memory, OCR,
multimodal behavior, or any Plan 4+ runtime. It does not read `.env`, real
credentials, paid Providers, network Tools, or `backend/ai_agent_lab.db`.

## Acceptance Matrix

| Step | Requirement | Current evidence | Gap | Minimal closure |
|---|---|---|---|---|
| S1 | Data model, Knowledge Base API, Document API tests | Model/schema/migration/service/API suites cover constraints, ownership, CRUD/upload, rollback, duplicates, safe errors, and limits | No fresh M6 evidence | Run the complete relevant set and record its exact result; add tests only for a discovered behavior gap |
| S2 | Parser, Cleaner, Chunker tests | Markdown/TXT/PDF, cleaning, metadata remapping, limits, overlap, Unicode and error paths already have focused suites | No fresh M6 evidence | Run all processing suites together and preserve the known text-layer-PDF/OCR boundary |
| S3 | Embedding, VectorStore, ingestion, Retriever tests | Provider/Registry/factory/adapter, Qdrant mapping, payload, pipeline compensation and Retriever isolation/error paths are covered | No fresh M6 evidence | Run Mock-focused suites and a cleaned temporary-Qdrant acceptance; do not call a live Embedding service |
| S4 | RAG Query/Chat/Tool tests | Prompt/schema/service/API/Tool/Agent tests cover retrieval, answer/source metadata, `RagQuery` persistence, rollback and lazy Tool wiring | No fresh M6 evidence | Run the complete set and record exact result; retain Mock LLM/Embedding boundaries |
| S5 | Frontend checks and Demo evidence | Knowledge/RAG frontend has unit/DOM tests and prior temporary browser checks | No committed Plan 3 release screenshots or final reproducible Demo record | Run typecheck/test/build, exercise a synthetic browser flow, and commit sanitized Knowledge and RAG screenshots |
| S6 | README/docs/CHANGELOG/version/tag/bridge closure | Plan 3 formal docs exist, but development remains under `[Unreleased]`, runtime metadata is `0.2.1`, Batch 16 is open, and `v0.3.0` does not exist | Release metadata, final review, bridge matrix, and tag handoff are missing | TDD the `0.3.0` metadata update, publish release docs/review evidence, verify tag absence honestly, and leave commit/tag creation to the user |

## Alternatives Considered

### 1. Evidence-First Release Closure — Chosen

Treat existing high-value tests as the acceptance asset, run every suite named
by S1～S4, and add code/tests only when a real gap appears. Add one release
contract RED/GREEN cycle for version synchronization, then spend the remaining
effort on an end-to-end Mock Demo, durable screenshots, documentation, bridge
checks, and complete regression. This maximizes evidence without inflating the
suite with duplicate assertions.

### 2. Add New Tests To Every Existing Test File

This would increase the test count but mostly restate behavior already covered
by hundreds of focused cases. It adds maintenance cost without proving a new
acceptance property, so it is rejected unless the audit identifies a specific
missing behavior.

### 3. Introduce A New Browser E2E Framework

A committed browser harness could be useful later, but M6 needs release Demo
evidence, not a new test subsystem. The existing Vitest/jsdom suite plus a
sanitized Playwright acceptance is sufficient and keeps Plan 3 small.

## Chosen Design

### 1. Test Closure Is An Audit, Not Test-Count Growth

S1～S4 map the execution table to concrete existing tests. Each group runs as a
single focused command so its pass count is attributable to the Step. If a
failure exposes a production bug, the fix begins with a minimal regression
test and follows RED/GREEN/REFACTOR. A passing, already comprehensive group is
recorded as accepted evidence rather than modified for appearance.

The release version is a genuine missing invariant. Update
`backend/tests/test_release_version.py` first to expect `0.3.0`, observe the
expected mismatch, then minimally synchronize backend package metadata,
FastAPI OpenAPI metadata, frontend package metadata, and lockfile root
metadata.

### 2. Demo And Screenshot Boundary

The release Demo uses synthetic Knowledge Base, Document, Conversation, RAG
answer, source, usage, and audit identifiers. Browser API responses are
intercepted locally, so screenshots cannot disclose real prompts, files,
credentials, database contents, or Provider output. The committed assets are:

- `docs/assets/plan3/knowledge-base-workspace.png`
- `docs/assets/plan3/rag-chat-sources.png`

The first shows Knowledge Base creation/selection, supported upload types, and
a completed Document lifecycle. The second shows a grounded answer, ordered
source card, score/provenance metadata, and correlation IDs. Desktop is the
canonical release view; narrow layout is also checked and recorded even if it
does not require another committed image.

The backend acceptance separately uses system-temporary SQLite/workspace data,
deterministic Mock LLM/Embedding implementations, and a random temporary Qdrant
collection. Cleanup must delete and recheck the collection and remove all
temporary files. The protected user SQLite database is never opened.

### 3. Release Documentation And Honest Tag State

`CHANGELOG.md` promotes the Plan 3 entries from `[Unreleased]` to
`[0.3.0] - 2026-08-02`. README files identify the Plan 3 release candidate and
show the complete create/upload/ask/source flow, screenshots, supported formats,
and limitations. Architecture and RAG documents record final verification and
Plan 4 bridge readiness. A formal Codex-only final review classifies findings
as must-fix, fix-later, recorded limitation, or not applicable.

Repository policy reserves stage/commit/push/tag for the user. Therefore M6 S6
can prepare and verify every tracked release artifact, but the final Plan 3
completion claim remains conditional until the user creates a commit and the
annotated `v0.3.0` tag at that commit. Documentation must not claim that the tag
already exists while it is absent.

### 4. Plan 4 Bridge Gate

The final review explicitly rechecks the five Plan 3 bridge contracts:

1. `search_knowledge_base` uses the shared retrieval/audit path.
2. `RagQuery` preserves query, requested Top-K, ordered retrieved sources,
   optional Conversation/answer linkage, and retrieval latency.
3. `DocumentChunk` preserves Document ownership, order, content, metadata, and
   vector ID.
4. RAG Query/Chat responses preserve sources plus retrieval metadata and audit
   identity.
5. Qdrant payloads preserve Knowledge Base, Document, and Chunk IDs.

The gate verifies extensibility only; it does not implement Trace, Advanced
RAG, reranking, or evaluation.

## Verification Strategy

Fresh completion evidence includes:

- S1～S3 and S4 focused backend groups;
- frontend typecheck, complete Vitest suite, production build, desktop/narrow
  browser acceptance, and visual inspection of both committed images;
- full backend pytest and `pip check` from safe temporary state;
- temporary SQLite Alembic upgrade/current/check/downgrade/re-upgrade;
- Compose config, Qdrant running/restart/loopback/health checks, and a cleaned
  temporary collection acceptance;
- all Markdown reads and local links/images;
- release version consistency and `v0.3.0` tag state;
- high-confidence secret/private-key, later-Plan runtime, network Tool, and
  tracked/untracked artifact scans;
- `git diff --check`, exact changed-path review, staged-path count, branch,
  HEAD/origin, and Codex final self-review.

