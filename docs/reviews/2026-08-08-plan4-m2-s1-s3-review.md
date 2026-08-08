# Plan 4 M2 S1～S3 LLM Trace Review

## Decision

`P4-M2-S1～S3` is complete with no remaining must-fix finding. Non-streaming
Chat, streaming Chat, and the final LLM call inside Naive RAG Chat now persist
standardized successful and Provider-failed Trace Runs/Steps. Existing API/SSE
responses, operational `LLMCall`/`RagQuery` records, and rollback behavior are
preserved.

The batch stays within Plan 4 M2 S1～S3. It does not implement Agent/Tool Trace
hooks, retrieval candidate models/Steps, Trace API/UI, Advanced RAG, reranking,
evaluation, Memory, or later runtime. After the user's manual commit,
`P4-M2-S4～S6` may begin.

## Scope And Git Baseline

- Branch: `main`.
- Baseline HEAD and `origin/main`:
  `c68d05968291fe9cfa5996d88b3bd31c30a0d43b`.
- Annotated `v0.3.1^{}`:
  `6bcf423434556f0862b7047b2dae1d6f26865c08`.
- Staged paths remained zero throughout the batch.
- `PROJECT_LEARNING_CHECKLIST.md` was a pre-existing user-owned untracked path;
  its contents were not read and the file was not modified.
- No branch, worktree, stage, commit, push, pull, rebase, merge, or tag mutation
  was performed.

## Acceptance Matrix

| Step | Requirement | Implementation | Fresh evidence | Result |
|---|---|---|---|---|
| P4-M2-S1 | One Chat LLM call creates an LLM Trace Step | Service-level `LLMTraceRecorder`; non-streaming/streaming Chat and final RAG Chat LLM hooks | Service/API success and failure tests in the 159-test matching group | complete |
| P4-M2-S2 | Standard prompt version, Provider/model, usage, cost, and latency metadata | `prompt_version.py`; strict frozen LLM metadata schemas; Run metric copy | Exact JSON, invalid-value, unknown-field, and persistence tests | complete |
| P4-M2-S3 | Mock Provider errors create failed Trace state safely | Rollback/recreate/commit failure audit with class-name-only error | New/existing Conversation, streaming, RAG, invalid response, redaction, and rollback-failure tests | complete |

## Delivered Contracts

- Stable prompt identifiers are `chat-history-v1` and `naive-rag-v1`.
- Every approved attempted LLM call owns exactly one `llm_call` Step.
- Step input contains only Provider, requested model, prompt version, stream
  flag, and message count.
- Step output contains only Provider, resolved model, prompt version, usage,
  fixed eight-decimal estimated cost, and Provider latency.
- Completed Run totals copy the single LLM call's token/cost values and retain
  the valid Conversation/user Message correlations.
- Successful business and Trace rows share the caller's existing transaction.
- Provider failures snapshot safe data, roll back provisional business/Trace
  rows, recreate one failed audit transaction, and re-raise the original
  Provider exception.
- Failed new Chat is uncorrelated. Existing Chat/RAG failure retains only its
  valid Conversation correlation; the rolled-back user Message is never linked.
- Raw Provider diagnostics, full Chat history, RAG context/source bodies,
  credentials, and arbitrary payloads are excluded from Step JSON and logs.
- Failure-audit persistence is best-effort and cannot mask the original
  Provider error, including when `Session.rollback()` itself fails.

## RED/GREEN Evidence

1. Prompt/schema RED: `test_llm_trace.py` failed collection because the prompt
   module and strict metadata schemas did not exist. GREEN: 50 selected tests
   passed.
2. Recorder/non-streaming Chat RED: selected tests failed because
   `LLMTraceRecorder` did not exist. The first implementation run exposed an
   eager package-export import cycle; the ORM-dependent Recorder remained a
   direct module import while dependency-light constants/enums stayed package
   exports. GREEN: 76 selected tests passed.
3. Streaming/RAG RED: 12 Trace assertions failed while 49 existing behavior
   tests passed. GREEN: the complete matching group initially passed 158 tests.
4. Codex self-review RED: a new rollback-failure test proved that the first
   audit rollback could mask the Provider error. After moving all audit
   rollback work behind the best-effort boundary, the isolated test and 71
   related tests passed.
5. Final post-fix GREEN: 159 matching tests and 1123 full-backend tests passed.

## Fresh Verification

- Matching backend:
  `159 passed, 1 Starlette/httpx TestClient deprecation warning`.
- Full backend from a unique system-temporary working directory with synthetic
  SQLite and a temporary `uploads` root:
  `1123 passed, 1 same warning`.
- The first environment-isolation attempt used a temporary directory named
  `documents`; one configuration test correctly rejected that non-default
  basename. The rerun used a temporary `uploads` directory, preserving both
  isolation and the documented default contract. All temporary directories
  were path-validated and removed.
- `pip check`: `No broken requirements found.`
- `git diff --check`: passed.
- Markdown/local-link scan: 134 Markdown files, 138 local links/images, zero
  missing. The user-owned checklist was excluded without reading its contents.
- Changed-text secret/private-key scan: zero high-confidence hits. New network
  client imports: zero.
- Scope/artifact scan: zero migration, frontend, Agent/Tool, API/model,
  generated-artifact, and `backend/ai_agent_lab.db` status paths.
- Staged paths: zero. Branch/HEAD/origin/tag refs remained at the stated
  baseline.
- Migration lifecycle: not applicable because no ORM schema, migration, or
  database constraint changed.
- Frontend typecheck/Vitest/build and browser screenshots: not rerun because
  this backend-only batch does not change a frontend/API response/UI contract.
- Docker/Qdrant smoke: not rerun because vector storage and retrieval behavior
  are unchanged; the RAG hooks begin only immediately before the LLM call.

## Findings And Disposition

| Severity | Disposition | Finding | Evidence and resolution |
|---|---|---|---|
| Important | must fix — fixed | The initial failure-audit rollback was outside the best-effort guard and could mask a Provider exception if rollback failed. | A dedicated RED test reproduced the leak. `LLMTraceRecorder.persist_failure()` now protects initial and cleanup rollback; GREEN and full regression passed. |
| Minor | recorded limitation | Early streaming consumer cancellation leaves no durable Trace. | This is the approved S1～S3 transaction boundary; cancellation persistence needs a separate lifecycle contract and remains later work. |
| Minor | fix later | Agent/Tool calls and retrieval candidates/prompt/source Steps are not traced. | Agent/Tool is outside this batch; retrieval Trace belongs to P4-M2-S4～S6. |
| Minor | fix later | No Trace API or Timeline UI exposes the new records yet. | P4-M2-S7～S10 owns query/UI and final M2 review. |
| Minor | recorded limitation | One dependency warning remains. | Existing Starlette TestClient/httpx deprecation warning; no new warning was introduced. |
| — | not applicable | Migration, frontend, browser, and live Qdrant verification. | No schema, frontend, response, retrieval, vector, or deployment behavior changed. |

No Critical finding was discovered. No Important finding remains open.

## Codex Self-Review

- All three approved LLM paths and both success/failure contracts have direct
  service/API or Recorder tests.
- Provider adapters, ORM models, Alembic migrations, route responses, frontend,
  Agent/Tool runtime, retrieval candidate behavior, and later runtime are
  unchanged.
- Trace routes remain thin by absence: all new orchestration lives in services
  and the Recorder; Providers have no SQLAlchemy/Trace dependency.
- Success and failure transaction boundaries, valid/invalid correlations,
  error redaction, cancellation rollback, retrieval-before-call failure, and
  audit rollback failure are directly exercised.
- Documentation describes current behavior and explicit later-batch limits.
- No real Provider, paid API, network Tool, real `.env`, credentials, user
  database, or user-owned checklist content was accessed.
- Codex was the only review gate; no external review was requested or used.

Conclusion: self-review has no remaining blocking issue.

## Next-Step Gate

`P4-M2-S4～S6` may begin after the user manually commits this batch. That batch
should add retrieval run/candidate persistence and Naive Retriever/
Prompt/Answer Trace contracts without changing the stable LLM Recorder contract
delivered here.

## Git Handoff

Codex did not stage or commit. Suggested manual commit message:

```text
feat(observability): trace chat llm calls
```
