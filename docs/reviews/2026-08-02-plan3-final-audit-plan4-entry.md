# Plan 3 Final Audit And Plan 4 Entry Review

## Decision

The complete Plan 3 implementation was independently audited against the
original Plan 3 design, execution table, `v0.2.1..v0.3.0` Git range, runtime
contracts, tests, release artifacts, and five Plan 4 bridge requirements. Two
Important Plan 3 findings were reproduced and fixed through behavior-level
RED/GREEN cycles. Fresh matching, full regression, migration, Qdrant, browser,
documentation, security, and Git-scope gates now show no remaining must-fix.

This audit does not implement Trace, Advanced RAG, hybrid retrieval, query
rewrite, parent-child retrieval, reranking, evaluation, Memory, OCR,
multimodal behavior, MCP, Human Approval, Browser Use, or any other Plan 4+
runtime. It uses Codex self-review only.

## Git Baseline And Scope

- branch: `main`;
- Plan 2 base / `v0.2.1^{}`: `872310b4dc1b78e2a2487303699d68ec8b22f88b`;
- initial HEAD / annotated `v0.3.0^{}`:
  `46ea94afe49c1db9179bbdb9a98093c86206b99f`;
- initial status and staged paths: clean / zero;
- `origin/main`: `a9c7fa5e1c000dce1ef369ef2fb8f25ba0b5386b`;
- `v0.1.0^{}` / `v0.2.0^{}` remained `4802d434...` / `0e3f3a66...`.

No branch/worktree/stage/commit/push/pull/rebase/merge/tag operation was
performed. The protected user database and real `.env`/credentials were not
read or modified.

## Acceptance Matrix

| Audit dimension | Original acceptance requirement | Implementation location | Fresh evidence | Gap / disposition |
|---|---|---|---|---|
| Plan completeness and boundary | Knowledge Base, ingestion, Embedding/VectorStore, Naive RAG, Tool, UI, tests/docs/release; no Plan 4 runtime | `backend/app/`, `frontend/src/`, `docs/`, Plan 3 execution table | `v0.2.1..v0.3.0` commit/file inventory plus full regression | Complete; later-Plan names are negative documentation only |
| Models and migrations | Strong ownership/FKs, duplicate hash, delete rules, RagQuery answer linkage, rollback ownership | `backend/app/models/`, Alembic `0005`～`0007`, services/routes | temporary SQLite full lifecycle and model/migration/API tests | Complete; head remains `20260801_0007` |
| Upload and controlled storage | Canonical UUID path, file/count/processing limits, duplicate/race normalization, safe failed state, cleanup | Document storage/service/ingestion/session callbacks | focused and full backend negative-path tests | Complete; concurrent cap check remains a local single-user limitation |
| Parser/Cleaner/Chunker | MD/TXT/text-layer PDF, Unicode/provenance/line/page metadata, bounded resources, explicit scanned-PDF failure | `backend/app/rag/parsers/`, Cleaner, Chunker | full backend parser/processing suites | Complete; OCR explicitly excluded |
| Embedding contract | ordered batch/query vectors, actual model identity, dimension, Registry/factory, safe errors/secrets | `backend/app/providers/embedding/` and ingestion/retrieval composition | adapter/provider tests plus identity RED/GREEN | Important identity propagation gap fixed |
| Qdrant | compatible collection, dimension/distance, traceable payload, ownership/model filters, delete/isolation/cleanup/restart | `backend/app/rag/vectorstores/` | `28` adapter tests, live disposable collection, Docker health | Important concurrent create race fixed |
| Retriever/Prompt/RAG | one query embedding, Top-K/threshold/order/zero-hit, bounded Prompt, audit/Conversation/answer linkage, rollback | Retriever, Prompt, `RagQueryService`/`RagService`, RAG route/schema | matching `277 passed`; full rollback/API tests | Complete; Naive vector strategy only |
| Agent Tool | bounded read-only search, canonical UUID/query/Top-K, lazy wiring, existing Agent loop compatibility | `backend/app/tools/builtin/search_knowledge_base.py`, dependencies | Tool/Agent tests included in matching gate | Complete; no new Agent state or network Tool |
| Frontend | loading/empty/error/success, upload status, source/audit IDs, responsive/reset behavior | Knowledge/RAG pages, store, source components, typed APIs | typecheck, `25 files / 149 tests`, build, headed browser | Complete; embedding identity now visible in each source |
| Test quality | real contracts, negative paths, uniqueness/ownership/transactions/races, no count-only duplication | Plan 3 backend/frontend tests | new tests target two reproduced faults; full `1030 passed` | Complete; known Starlette/httpx warning only |
| Docs and release truth | README/docs/CHANGELOG/env/screenshots/links/version/limitations match current state | README files, docs 01/20～23, CHANGELOG, review, execution table | Markdown/local-link scan and visual screenshot review | Complete; tag impact recorded explicitly |
| Security and hygiene | no secrets/user DB/paid Provider/network Tool/generated artifacts/Plan 4 runtime | tracked diff and runtime boundaries | secret/private-key/artifact/later-Plan scans | Complete; 14 private-key headers are denylist/test/history literals |
| Plan 4 bridge | shared retrieval, durable audit, source-rich chunks, traceable responses, traceable payload | Tool/RAG service, RagQuery/DocumentChunk, schemas, payload | tests, API/browser evidence, live adapter smoke | All five stable after fixes |

## Findings And Disposition

### Important — Must Fix — Fixed

1. **Embedding model identity was not part of storage or retrieval isolation.**
   Before the repair, a deterministic in-memory reproduction indexed `model-a`
   and `model-b` vectors with the same dimension in one Knowledge Base and both
   were accepted; payloads contained no embedding identity. This could compare
   unrelated vector spaces, corrupt result quality, and make RagQuery/Plan 4
   evidence irreproducible. The repair persists normalized Provider plus the
   actual returned model at `backend/app/rag/ingestion_pipeline.py:51` and
   `backend/app/rag/vectorstores/payload.py:40`, requires both in
   `VectorSearchQuery` and Qdrant filters at
   `backend/app/rag/vectorstores/base.py:69` and
   `backend/app/rag/vectorstores/qdrant_store.py:131`, rejects mismatched
   responses in Qdrant and Retriever, and exposes the identity through RAG
   schemas/UI/audit snapshots. Negative tests are at
   `backend/tests/test_qdrant_vector_store.py:456` and
   `backend/tests/test_retriever.py:403`.

2. **Compatible concurrent first-collection creation failed unnecessarily.**
   Two first uploads could both observe a missing collection; the loser treated
   the create conflict as a terminal VectorStore failure. With the Plan 3 hash
   uniqueness rule and no retry/delete API, the failed Document could not be
   cleanly re-uploaded. The adapter now re-reads after an uncertain create and
   proceeds only if the winning collection has the exact expected configuration
   (`backend/app/rag/vectorstores/qdrant_store.py:75`). Compatible recovery and
   incompatible fail-closed coverage are at
   `backend/tests/test_qdrant_vector_store.py:199` and `:216`.

### Minor — Recorded Limitations

- Points written before embedding identity became a required payload/filter do
  not match repaired queries and require re-ingestion
  (`docs/21-embedding-provider.md:154`). No unsafe compatibility fallback is
  used.
- The per-Knowledge-Base file cap is enforced by a count-before-create check
  (`backend/app/services/document_service.py:111`), not a database counter;
  unsupported concurrent writers near the cap could exceed it by a small
  amount. SQLite remains the supported local single-user deployment boundary.
- Hard process failure after Qdrant write can still leave orphan points; normal
  request rollback and uncertain-upsert paths are compensated best-effort.
- RAG turns/sources remain current-session only; Document delete/re-ingestion
  management and live paid Provider quality/cost acceptance remain absent.

### Fix Later / Not Applicable

- Advanced RAG, hybrid search, query rewrite, parent-child retrieval, reranking,
  evaluation, and Trace runtime belong to Plan 4 and were not implemented.
- OCR, multimodal, Memory, MCP, Human Approval, Browser/Computer Use, PostgreSQL
  migration, real Provider/network Tool calls, and external review are not
  applicable to this Plan 3 audit.

## TDD Evidence

- Embedding identity RED: builder rejected identity arguments and the immutable
  search contract rejected both fields (`3 failed`). GREEN: adjacent
  payload/Qdrant/ingestion/Retriever/RAG group first reached `138 passed`, then
  `142 passed` after negative identity/audit assertions.
- Frontend identity RED: typecheck rejected identity fields as unknown. GREEN:
  typecheck and targeted source-card Vitest (`3 passed`) succeeded after type
  and presentation propagation.
- Concurrent collection RED: compatible concurrent creation reproduced one
  `VectorStoreOperationError`. GREEN: complete Qdrant adapter suite reached
  `28 passed`, including incompatible-winner rejection.
- Final matching group: `277 passed, 1 warning`.

## Final Verification Evidence

- backend full regression from a system-temporary working directory:
  `1030 passed, 1 warning` in 37.75 seconds;
- dependency integrity: `No broken requirements found.`;
- frontend: typecheck passed; Vitest `25 files / 149 tests`; production build
  transformed `1826` modules. The sandbox build's only failure was confirmed
  `EPERM` writing ignored `dist/assets`; the identical approved build passed;
- temporary SQLite: upgrade head, `current --check-heads`, `alembic check`,
  downgrade `0007 -> 0006`, re-upgrade and final head `0007` all passed; the
  temporary directory was removed;
- Docker/Qdrant: client/server `29.6.2`, Compose config valid,
  `qdrant/qdrant:v1.15.4` running, restart `0`, only
  `127.0.0.1:6333`, health HTTP 200;
- live production-adapter smoke: one random collection stored same-KB
  `model-a`/`model-b` plus a foreign-KB point, returned only the requested
  identity, preserved non-target points after Document deletion, then confirmed
  final collection absence;
- clean headed browser: desktop `1440x900` and narrow `390x844` had no horizontal
  overflow, source identity and all audit IDs were visible, `New RAG chat`
  reset succeeded, all 11 local mocked API requests returned 200, and the clean
  session had zero console warnings/errors. The affected formal RAG screenshot
  was replaced and visually inspected;
- docs: 121 Markdown files and 103 local links/images, zero missing;
- security/hygiene: high-confidence tokens zero, tracked artifacts zero, no
  executable later-Plan/network-Tool addition. Fourteen private-key header hits
  are known denylist/test/historical documentation literals, not key material.

## Plan 4 Bridge Decision

| Bridge | Final decision |
|---|---|
| Shared Agent/RAG retrieval | Stable: Tool delegates to the same `RagQueryService` and remains lazy/read-only |
| Persisted retrieval audit | Stable: query, KB, Top-K, ordered sources including embedding identity, latency, and optional answer linkage persist |
| Source-rich chunks | Stable: Document/KB ownership, order, content, heading/page/metadata, and vector ID remain intact |
| Traceable RAG responses | Stable: Query/Chat/Tool return ordered sources, strategy/Top-K/count/audit IDs, and embedding identity |
| Traceable vector payload | Stable: KB/Document/Chunk plus Provider/actual-model identity and full source payload are validated and filtered |

## Release And Entry Conclusion

Plan 3 has no remaining must-fix and all five Plan 4 bridge contracts are
stable. After the user manually records this verified audit repair in Git, the
workspace can enter `P4-M1-S1～S3`; this review does not start those Steps.

Annotated `v0.3.0` still points to the pre-repair release commit `46ea94a`.
Codex did not move it. If that tag has never been published, the user may choose
to replace it manually after committing; if it has been published, preserve it
and publish a follow-up `v0.3.1` instead.

Suggested commit message:

```text
fix(rag): harden vector identity and collection races
```
