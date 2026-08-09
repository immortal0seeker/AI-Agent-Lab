# Plan 4 M2 S7～S9 Trace API And Timeline Review

## Decision

`P4-M2-S7～S9` is complete with no remaining must-fix finding. The backend now
exposes bounded, read-only Trace list/detail APIs, and the fourth frontend
workspace replays persisted Run, Step, retrieval, and candidate evidence with
stable IDs and deep links.

This batch does not implement the S10 Trace usage document or M2 final review,
Agent/Tool Trace runtime, Advanced RAG, reranking, evaluation, or any Plan 5
capability. `P4-M2-S10` is the next eligible Step.

## Scope And Git Baseline

- Branch: `main`.
- Baseline HEAD and `origin/main`:
  `93d9b6bb34109e0e3eba254a4e5f4df00f3b548d`.
- Staged paths remained zero throughout the batch.
- No branch, worktree, stage, commit, push, pull, rebase, merge, or tag mutation
  was performed.

## Acceptance Matrix

| Step | Requirement | Implementation | Fresh evidence | Result |
|---|---|---|---|---|
| P4-M2-S7 | Add read-only Trace query APIs | `TraceQueryService`, strict response schemas, thin `/api/v1/traces` routes, safe 404/422/503 envelopes | schema/service/API tests, four-query assertion, full backend regression | complete |
| P4-M2-S8 | Add frontend Trace types and API client | strict Run/Step/retrieval/candidate types, normalized API errors, shared workspace/run URL helpers | API, URL, App, and typecheck tests | complete |
| P4-M2-S9 | Add Trace Timeline workspace | independent list/detail states, deep-link restore, stale-response guards, ordered Step/candidate rendering, responsive layout | component/page DOM tests plus headed desktop/mobile browser acceptance | complete |

## Delivered Contracts

- `GET /api/v1/traces?limit=50` accepts limits from 1 through 100, orders Runs
  by `created_at DESC, id DESC`, and caps Unicode `input_preview` at 160
  characters.
- `GET /api/v1/traces/{trace_run_id}` returns the full persisted Run, Steps by
  `step_index, id`, retrieval Runs by `created_at, id`, and candidates by
  `rank, id`. Unknown UUIDs use `trace_run_not_found`; malformed input uses the
  shared validation envelope.
- Detail loading uses at most four deterministic SQLite queries and has no LLM,
  Embedding, Qdrant, or external-network dependency.
- The detail response contains persisted 500-character candidate previews and
  allowlisted metadata only. It does not reconstruct prompts, full RAG context,
  vector payloads, or deleted source records.
- The Trace workspace uses `?workspace=trace&run=<uuid>`, restores Runs outside
  the recent 50, preserves unrelated URL state, and clears incompatible Agent
  or Trace `run` values when switching workspaces.
- List and detail loading/error/retry states are independent. Generation guards
  reject stale responses and updates after unmount.
- The Timeline preserves Run, Step, retrieval, candidate, Knowledge Base,
  Document, and Chunk IDs; displays failed states and zero-candidate Runs; and
  associates retrieval evidence through `output_json.retrieval_run_id`.

## RED/GREEN Evidence

1. Backend schema/service RED: imports failed because the Trace query schemas
   and service did not exist. GREEN: 107 related tests passed.
2. Backend route RED: dependency/router contracts were absent. GREEN: 97
   selected tests passed with the one existing TestClient warning.
3. Frontend types/API/navigation RED: Trace modules were absent and eight URL
   or navigation assertions failed. GREEN: 17 tests and typecheck passed.
4. Timeline RED: component/page modules were absent and seven rendering/state
   assertions failed. GREEN: 15 tests, later expanded to 28 selected tests.
5. Self-review RED: frontend detail types incorrectly required the list-only
   `input_preview`; typecheck failed after fixtures were corrected to the real
   API response. GREEN: `TraceRunDetail` now omits that field, the title falls
   back to `input_text`, 12 related tests and typecheck passed, and the backend
   API test asserts the field is absent.

## Fresh Verification

- Matching backend: `223 passed`, with one existing Starlette/httpx TestClient
  deprecation warning.
- Full backend from a unique system-temporary SQLite URL and upload root:
  `1198 passed`, with the same warning. `pip check` reported no broken
  requirements, and the validated temporary directory was removed.
- Temporary SQLite migration lifecycle passed upgrade head,
  `current --check-heads`, `alembic check`, downgrade one revision, re-upgrade,
  and final head verification at `20260808_0009`; the temporary directory was
  removed.
- Frontend typecheck passed; Vitest passed 31 files / 172 tests; the production
  build transformed 1832 modules. A first sandboxed build hit Windows `EPERM`
  while recreating `dist/assets`; the same build passed outside the sandbox,
  identifying an environment restriction rather than a source failure.
- Headed browser acceptance passed at 1440×900 and 390×844 with synthetic
  records: automatic selection, deep-linked failed Run, ordered Steps and
  candidates, expanded metadata, zero console errors/warnings, successful API
  requests, and zero horizontal overflow.
- Markdown/local-link scan: 139 Markdown files, 162 local links/images, zero
  missing. The 39-path change set had zero high-confidence secret/private-key,
  later-Plan runtime path, tracked/visible temporary artifact, generated DB, or
  leftover Playwright file hits; `git diff --check` passed and staged paths
  remained zero.
- Docker/Qdrant smoke was not rerun because these APIs read SQLite persistence
  only and tests prove they do not initialize Provider or VectorStore
  dependencies. No real Provider or network Tool was called.

## Findings And Disposition

| Severity | Disposition | Finding | Evidence and resolution |
|---|---|---|---|
| Important | must fix — fixed | Frontend detail types inherited list-only `input_preview`, so runtime data and the TypeScript contract disagreed. | Corrected fixtures first reproduced the type error. `TraceRunDetail` now omits the field, the UI uses `input_text`, and focused plus full regressions passed. |
| Minor | recorded limitation | Agent/Tool execution still has no shared Trace Run/Step lifecycle. | This batch only reads already-persisted evidence. Agent/Tool Trace requires a separately designed transaction boundary. |
| Minor | recorded limitation | Generic Trace lifecycle still has no automatic multi-Step cost aggregation or durable cancellation policy, and Prompt-construction failure before an LLM attempt is unpersisted. | Existing M2 scope is unchanged; the Timeline faithfully reports available persisted evidence. |
| Minor | fix later | Dedicated Trace usage documentation and the M2 final review are not present. | `P4-M2-S10` owns both deliverables. |
| Minor | fix later | Advanced retrieval, reranking, and evaluation are not displayed because their runtimes are not implemented. | These belong to later Plan 4 milestones; no placeholder runtime was added. |
| Minor | recorded limitation | One dependency warning remains. | Existing Starlette TestClient/httpx deprecation warning; no new warning was introduced. |
| — | not applicable | Live Provider/Qdrant verification for the Trace read surface. | The implementation is SQLite-only and dependency-isolation tests fail if Provider or VectorStore construction occurs. |

No Critical finding was discovered. No Important finding remains open.

## Codex Self-Review

- The diff is limited to P4-M2-S7～S9 read APIs, typed frontend client,
  Timeline workspace, tests, screenshots, and current-scope documentation.
- Routes remain thin; ordering, grouping, preview truncation, and query bounding
  live in a separately tested service.
- Response schemas reject unexpected or invalid values, and errors do not leak
  database diagnostics or runtime Provider configuration.
- Detail retrieval is bounded and avoids N+1 queries. The frontend sorts
  persisted Steps/candidates defensively and preserves every traceable ID.
- Loading, empty, error, success, failed Run/Step, zero-candidate, deep-link,
  retry, stale-response, unmount, desktop, and mobile paths have direct
  evidence.
- No migration, persistence-write contract, Provider, vector-store adapter,
  Agent runtime, Tool runtime, Advanced RAG, evaluation, or later-Plan behavior
  was added.
- No real `.env`, secret, API key, user database, Provider, network Tool,
  browser credential, or system credential was accessed.
- Codex was the only review gate; no external review was requested or used.

Conclusion: self-review has no remaining blocking issue.

## Next-Step Gate

`P4-M2-S10` may begin after the user manually commits this batch. M3 should not
begin before S10 completes the dedicated usage documentation and M2 final
review.

## Git Handoff

Codex did not stage or commit. Suggested manual commit message:

```text
feat(observability): add trace api and timeline
```
