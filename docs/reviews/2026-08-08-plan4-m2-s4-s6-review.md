# Plan 4 M2 S4～S6 RAG Trace Review

## Decision

`P4-M2-S4～S6` is complete with no remaining must-fix finding. Standalone RAG
Query now persists one Trace Run, one retrieval Step, one retrieval audit Run,
and ordered candidate snapshots. RAG Chat reuses one Trace Run for retrieval,
Prompt construction, the existing LLM call, and final-answer linkage. Existing
RAG HTTP responses and the read-only Agent Tool contract are unchanged.

This batch does not implement P4-M2-S7 Trace APIs, S8 frontend types, S9
Timeline UI, Advanced Retrieval, reranking, evaluation, Agent/Tool Trace, or any
Plan 5 capability. After the user's manual commit, `P4-M2-S7～S9` may begin.

## Scope And Git Baseline

- Branch: `main`.
- Baseline HEAD and `origin/main`:
  `513e95bcf780b87c0ec6135cf554e45c1004beb0`.
- Staged paths remained zero throughout the batch.
- No branch, worktree, stage, commit, push, pull, rebase, merge, or tag mutation
  was performed.

## Acceptance Matrix

| Step | Requirement | Implementation | Fresh evidence | Result |
|---|---|---|---|---|
| P4-M2-S4 | Design retrieval Run/candidate persistence | `RagRetrievalRun`, `RagRetrievalCandidate`, strict schemas, Trace ownership, audit-preserving source snapshots, revision `20260808_0009` | Model/schema/migration tests plus full migration lifecycle | complete |
| P4-M2-S5 | Connect Naive Retriever Trace | Additive `RetrievalBatch`, `RAGTraceRecorder`, standalone Query and RAG Chat service hooks, durable safe retrieval failure | Recorder/service/API zero-hit, ordering, identity, rollback, redaction, and failure tests | complete |
| P4-M2-S6 | Connect RAG Prompt/Answer Trace | Ordered `build_prompt`, existing `llm_call`, and `final_answer` Steps; Provider-failure retrieval/Prompt replay | Prompt subset/truncation, linkage, success, invalid-response, and Provider-failure tests | complete |

## Delivered Contracts

- Revision `20260808_0009` creates retrieval Runs before candidates and drops
  them in reverse order. A Trace Run deletion cascades through both levels.
- Knowledge Base, Document, and Chunk identities are snapshots without source
  foreign keys, so completed retrieval evidence survives source deletion.
- `Retriever.retrieve_batch()` returns Provider/actual-model identity even for
  zero hits; the existing `retrieve()` tuple contract remains compatible.
- Naive Vector candidates preserve one-based rank/final-rank, dense score,
  selection, stable source IDs, a 500-character preview, and bounded metadata.
- Candidate nested metadata is restricted to `source_format`, `start_char`,
  `end_char`, and `heading_level`; raw payloads and arbitrary Chunk metadata are
  excluded.
- Successful RAG Query Step order is `rag_retrieve`. Successful RAG Chat order
  is `rag_retrieve -> build_prompt -> llm_call -> final_answer`.
- Prompt Trace stores version, counts, and ordered source identities/truncation
  facts, not the expanded Prompt or source bodies. Final-answer Step stores
  RagQuery/Message/LLMCall IDs and counts, not duplicate answer text.
- Retrieval failure durably stores a failed Run/Step with only the exception
  class. Provider failure replays completed retrieval candidates and Prompt
  metadata before the failed LLM Step while business rows remain rolled back.
- Successful writes remain caller-transaction-owned and flush-only. Failure
  audit persistence is best-effort and cannot mask the original exception.
- `search_knowledge_base` explicitly disables standalone Trace so an inner
  durable failure audit cannot commit the Agent-owned transaction early.

## RED/GREEN Evidence

1. Model/migration RED: three model assertions failed and 21 tests errored
   because retrieval models/migration were absent. GREEN: 51 related tests
   passed.
2. Schema/Retriever RED: schema import and `retrieve_batch()` were absent while
   all 29 legacy Retriever tests still passed. GREEN: 55 related tests passed.
3. Recorder RED: five tests failed because no RAG Trace Recorder existed.
   GREEN: all five passed.
4. Query/service/API RED: nine tests failed because tracing, durable failure,
   and the explicit Tool transaction policy were absent. GREEN: the first
   combined service/API group reached 101 passed.
5. Prompt/final-answer RED: two bottom-contract tests and then three integration
   assertions failed because the LLM recorder completed the Run early and no
   Prompt/final steps existed. GREEN: 82 related tests passed.
6. Provider-failure replay RED: five tests found only the failed LLM Step after
   rollback. GREEN: the completed retrieval/Prompt evidence now replays before
   the failed LLM Step.
7. Final post-documentation GREEN: 305 matching backend tests and 1173 full
   backend tests passed.

## Fresh Verification

- Matching backend: `305 passed`, with one existing Starlette/httpx TestClient
  deprecation warning.
- Full backend from a unique system-temporary SQLite URL and temporary
  `uploads` root: `1173 passed`, with the same warning. The validated temporary
  directory was removed.
- The first full-backend wrapper attempt was rejected as isolation evidence:
  this PowerShell version did not accept `New-Item -LiteralPath`, and its error
  mode allowed pytest to continue. The corrected wrapper used `-Path` plus
  terminating errors and produced the accepted result above.
- `pip check`: `No broken requirements found.`
- Temporary SQLite migration lifecycle: upgrade head, `current --check-heads`,
  `alembic check`, downgrade to `20260802_0008`, table-absence check, re-upgrade,
  final head/table-presence check all passed at `20260808_0009`; the temporary
  directory was removed.
- Frontend typecheck passed; Vitest passed 25 files / 149 tests; production
  build transformed 1826 modules.
- Markdown/local-link scan: 137 Markdown files, 149 local links/images, zero
  missing.
- Changed-path scan: 29 expected paths; zero high-confidence secret/private-key,
  new network client/Tool, unexpected generated-artifact, and later-Plan runtime
  path hits.
- Docker/Qdrant smoke was not rerun because no Qdrant adapter, vector payload,
  filter, collection, or deletion behavior changed; Mock Retriever boundaries
  directly cover the additive identity result.
- Browser/screenshots were not rerun because no frontend or RAG/Trace HTTP
  response changed and S7～S9 own the first Trace query/UI surface.

## Findings And Disposition

| Severity | Disposition | Finding | Evidence and resolution |
|---|---|---|---|
| Important | must fix — fixed | Provider-failure rollback initially discarded completed retrieval candidate and Prompt evidence. | Five RED tests reproduced the incomplete audit. The failed Run now recreates the same retrieval/candidate identities and completed Steps before the failed LLM Step; focused and full regression passed. |
| Important | must fix — fixed | Reusing traced `RagQueryService` inside the Agent Tool would let durable retrieval failure commit outside the Agent transaction. | A RED Tool dependency test fixed the policy: the lazy Tool executor now passes `trace_enabled=False`; untraced success/failure transaction tests passed. |
| Minor | recorded limitation | A Prompt-construction failure before any LLM attempt leaves no durable failed Trace. | The existing full-rollback contract is preserved. Durable mid-flow non-Provider failure policy needs a separately designed lifecycle and is not required by S4～S6. |
| Minor | fix later | Trace records have no public API or frontend Timeline. | P4-M2-S7～S9 own those surfaces. |
| Minor | fix later | Agent/Tool execution is not yet connected to Trace. | The Tool retains RagQuery audit only; Agent/Tool Trace must share one later transaction/lifecycle design. |
| Minor | recorded limitation | One dependency warning remains. | Existing Starlette TestClient/httpx deprecation warning; no new warning was introduced. |
| — | not applicable | Live Qdrant and browser acceptance for this batch. | No vector adapter/filter/payload or HTTP/frontend contract changed; matching mock and full regressions cover the touched seams. |

No Critical finding was discovered. No Important finding remains open.

## Codex Self-Review

- The diff is limited to P4-M2-S4～S6 retrieval persistence, Recorder/service
  orchestration, tests, migration, and current-scope documentation.
- Routes remain thin and unchanged; business transaction policy stays in the
  services/recorders. Provider and VectorStore implementations have no ORM or
  Trace dependency.
- Model, schema, migration, service, API, error, rollback, uniqueness,
  ownership, zero-hit, source-order, prompt-subset, source-deletion, and
  audit-replay contracts have direct tests.
- Existing Chat/streaming LLM Recorder callers retain default finish behavior;
  only RAG Chat opts into multi-Step Run completion.
- No full Prompt/context, raw vector payload, arbitrary metadata, Provider error
  body, secret, or credential is added to audit JSON or logs.
- No real Provider, paid API, network Tool, real `.env`, user database, browser
  credential, or system credential was accessed.
- Codex was the only review gate; no external review was requested or used.

Conclusion: self-review has no remaining blocking issue.

## Next-Step Gate

`P4-M2-S7～S9` may begin after the user manually commits this batch. The next
batch should expose read-only Trace Run/Step/candidate APIs and typed Timeline
UI without changing the persistence contracts delivered here.

## Git Handoff

Codex did not stage or commit. Suggested manual commit message:

```text
feat(observability): trace rag retrieval and answers
```
