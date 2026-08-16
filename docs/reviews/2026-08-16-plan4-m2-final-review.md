# Plan 4 M2 Trace Integration And Timeline Final Review

## Decision

**PASS.** `P4-M2-S1` through `P4-M2-S10` satisfy the approved Trace
integration, retrieval evidence, read API, Timeline, documentation, and review
scope. The independent audit found one Important M2 UI acceptance defect and
one Important documentation-drift finding; both were repaired and their
RED/GREEN assertions pass. No Critical or Important finding remains. Plan 4 M3 may begin at
`P4-M3-S1～S3`; no M3 runtime was implemented by this closeout.

Codex self-review was the only review gate. No external reviewer was requested,
run, awaited, cited, or used.

## Scope And Git Baseline

The reviewed M2 implementation range is `c68d059..be7ee17`:

- branch: `main`;
- M2 release HEAD: `be7ee17105ebd8421874e45eba565e1545b086e3`;
- `origin/main`: `be7ee17105ebd8421874e45eba565e1545b086e3`;
- Plan 3 hardening tag target `v0.3.1^{}`:
  `6bcf423434556f0862b7047b2dae1d6f26865c08`;
- range size: 71 changed paths, 11,712 insertions, and 113 deletions.

S10 changed one focused Timeline component, its DOM regression test, refreshed
two sanitized acceptance images, and the related documentation/planning/review
material: **14 working-tree paths** in total. It did not
stage, commit, push, pull, rebase, merge, change branches, or mutate tags.

## S1-S10 Acceptance Matrix

| Step | Acceptance contract | Implementation/evidence | Result |
|---|---|---|---|
| P4-M2-S1 | Chat and RAG Chat LLM calls write Trace Steps | `llm_trace.py`, Chat/RAG service wiring, focused/full tests | pass |
| P4-M2-S2 | Provider/model, prompt version, usage, cost, and latency use strict metadata | Trace schemas/recorder and schema/service tests | pass |
| P4-M2-S3 | Provider failure rolls back provisional business data and preserves safe failed Trace | failure replay tests; class-name-only error persistence | pass |
| P4-M2-S4 | Retrieval Run/candidate persistence and migration are stable | ORM/schema plus Alembic `20260808_0009` lifecycle | pass |
| P4-M2-S5 | RAG Query/Chat persist ordered retrieval candidates and source IDs | retrieval recorder, RAG Trace tests, failure coverage | pass |
| P4-M2-S6 | Prompt selection and final answer are linked to the same Trace | ordered `rag_retrieve`, `build_prompt`, `llm_call`, `final_answer` evidence | pass |
| P4-M2-S7 | Bounded read-only Trace list/detail API exposes deterministic evidence | thin routes, bounded service queries, API/service tests | pass |
| P4-M2-S8 | Frontend API/types preserve Run, Step, retrieval, candidate, and score contracts | TypeScript check and Vitest suite | pass |
| P4-M2-S9 | Timeline restores deep links and renders independent, responsive states plus Run token/cost/latency | DOM tests and fresh headed desktop/mobile acceptance | pass |
| P4-M2-S10 | Usage guide, current-status reconciliation, full verification, and Codex review exist | `docs/31-trace-timeline.md`, this review, final gates | pass |

## Delivered M2 Contracts

- LLM success records share the caller-owned transaction. Provider failure
  removes provisional business rows and persists only a normalized failed
  Trace envelope.
- Standalone RAG Query and RAG Chat persist the original query, strategy,
  embedding identity, bounded ordered candidate snapshots, stable source IDs,
  selected sources, latency, Prompt linkage, and answer linkage.
- Candidate previews are capped at 500 characters and metadata is allowlisted.
  Run-list input previews are capped at 160 Unicode characters.
- `GET /api/v1/traces?limit=50` accepts limits from 1 through 100 and orders
  Runs by `created_at DESC, id DESC`.
- Detail reads order Steps by `step_index, id`, retrieval Runs by
  `created_at, id`, and candidates by `rank, id`. The service performs no more
  than four deterministic SQLite queries for one detail response.
- Trace reads initialize no Provider or vector store and return safe 404/422/
  503 envelopes without leaking raw downstream diagnostics.
- `?workspace=trace&run=<uuid>` restores a Run outside the recent list. List
  and detail loading/retry states are independent and guarded against stale or
  unmounted responses.
- The Timeline displays input/output/total tokens, estimated cost, and Run
  latency, using an explicit `—` when a persisted metric is absent.

## Fresh Verification Evidence

All commands used synthetic credentials/data, system-temporary SQLite and
document roots, Mock Providers, and the built local frontend:

- focused M2 backend: **154 passed**, 1 known Starlette/httpx TestClient
  deprecation warning, 20.26 seconds;
- full backend: **1,198 passed**, the same single warning, 104.80 seconds;
- dependency integrity: `pip check` reported no broken requirements;
- temporary SQLite lifecycle: upgrade, `current --check-heads`, autogenerate
  `check`, downgrade one revision, re-upgrade, and final current all passed at
  `20260808_0009 (head)`;
- frontend typecheck: passed;
- frontend Vitest: **31 files / 173 tests passed**;
- production build: **1,832 modules transformed**, build passed after rerunning
  outside the Windows sandbox that denied `dist/assets` recreation;
- headed Chromium: 1440×900 and 390×844 passed with recent-Run URL selection,
  an out-of-list failed deep link, ordered four-Step RAG Chat Timeline, rank-1/
  rank-2 candidates, exact non-null score labels/IDs, visible Run token/cost/
  latency metrics, expandable Run/Step metadata, stacked mobile panes, and
  zero horizontal overflow;
- browser telemetry: **0 failed requests, 0 console errors, 0 console
  warnings**; health, list, selected detail, and deep-link detail requests all
  resolved from synthetic route mocks;
- the Important metrics repair materially changed the current UI, so fresh
  synthetic desktop/mobile acceptance assets replaced the stale images.
- documentation scan: **143 Markdown files / 181 local links and images / 0
  missing targets**, excluding fenced and inline code from link parsing;
- final hygiene: `git diff --check` and cached diff check passed; staged paths,
  secret/private-key hits, generated artifact hits, later-Plan runtime paths,
  and legacy external-review tokens were all zero.

The Timeline metrics repair followed strict TDD. RED added one DOM contract and
produced **1 failed / 6 passed** because the metrics region was absent. The
minimal component change then produced **7/7 passed**, followed by the complete
31-file/173-test frontend suite, typecheck, build, and headed browser GREEN.

The first isolated full-backend attempt used a temporary directory named
`documents`, which intentionally overrode the setting checked by the default
`uploads`-name test. That verifier-only mismatch produced 1 failure and 1,197
passes; changing only the temporary fixture path to `.../uploads` produced the
clean 1,198-pass result above. No product source was changed. Likewise, the
initial sandboxed Vite build failure was the known Windows `EPERM` on
`dist/assets`; the identical approved build passed outside the sandbox.

## Findings And Disposition

### Must Fix - Fixed

1. **Important — Run token/cost/latency were returned but not visible in the
   Timeline.** `TraceRunDetail` already preserved the fields, but
   `TraceTimelinePage.tsx` did not render them and the DOM suite did not assert
   the M2 visibility requirement. Impact: an operator could not inspect the
   Run-level resource evidence promised by the milestone. Disposition: added a
   focused failing DOM test, rendered the five persisted metrics with explicit
   unavailable states, then passed focused/full frontend and headed responsive
   verification. The desktop/mobile assets were refreshed with synthetic data.
2. **Important — current architecture/status documentation lagged the
   implementation.** The RED gate found two missing S10 artifacts, the stale
   assertion that Trace API/Timeline remained future M2 work in
   `docs/01-architecture.md`, and 31 legacy external-review references in the
   active Plan 4 execution table. Impact: a developer could incorrectly defer
   an implemented interface or treat an obsolete review process as a gate.
   Disposition: added the Trace Timeline guide and this review, corrected
   README/architecture/CHANGELOG/foundation status, and normalized the active
   execution table to Codex-only review. The documentation GREEN gate reports
   zero stale architecture and zero stale review-policy matches.

No Critical or Important finding remains.

### Fix Later

1. The single Starlette/httpx TestClient deprecation warning is dependency
   maintenance, not an M2 contract failure. Address it in a dedicated
   dependency-update batch with full compatibility testing.

### Recorded Limitations

1. Agent and Tool runtime do not yet write Trace Runs/Steps; Agent knowledge
   search retains its existing Agent-owned transaction.
2. Early streaming cancellation and Prompt-construction failure before the LLM
   attempt do not produce complete durable Trace evidence.
3. The recent list is bounded to 100 and M2 adds no pagination/export workflow.
4. The reader does not reconstruct full prompts, conversation context, vector
   payloads, raw Provider bodies, or deleted source documents.
5. Advanced Retrieval, Rerank, and Evaluation remain later Plan 4 work.

### Not Applicable

1. No backend TDD repair was needed because the audit reproduced no backend M2
   runtime defect. The UI acceptance gap and documentation drift each received
   an explicit RED/GREEN cycle.
2. No real Qdrant smoke was required: S10 changes no vector adapter or payload
   contract, and the Trace read surface is deliberately SQLite-only.

## Security And Plan Boundary Review

No real `.env`, credential, API key, SSH/browser/system credential store,
`backend/ai_agent_lab.db`, paid Provider, real network Tool, or Qdrant
collection was read or called. Tests used temporary storage and synthetic
identifiers. Trace APIs remain read-only and SQLite-only. Candidate metadata is
allowlisted, previews are bounded, and failure evidence remains class-name
only. No Metadata Filtering, BM25, Hybrid/RRF, Parent-Child, Query Rewrite,
Rerank, Evaluation, Agent/Tool Trace, Memory, Agent Runtime v2, Human Approval,
MCP, OCR, or multimodal runtime was added.

## Codex Self-Review

- The complete 71-path M2 range and all write/read/UI seams were inspected
  independently rather than accepting the three earlier batch reviews as the
  conclusion.
- Routes remain thin; transaction, failure replay, source identity, ordering,
  bounded preview, and no-N+1 query contracts are service/schema owned and
  covered by focused/full tests.
- Timeline IDs, deep links, independent async states, Step/retrieval/candidate
  order, failure rendering, metadata disclosure, and responsive overflow are
  covered by tests plus headed acceptance.
- The S10 diff contains one narrowly scoped Timeline metrics repair, its test,
  refreshed sanitized screenshots, and documentation/planning/review changes;
  it does not cross into M3 or a later Plan.
- Codex was the sole reviewer and all active Plan 4 review instructions now
  use Codex self-review.

**Self-review conclusion:** no remaining must-fix finding.

## M3 Entry Gate

The M2-to-M3 bridge is stable:

1. retrieval strategies can continue to write the same Trace Run/Step envelope;
2. persisted retrieval candidates already carry stable source, rank, score,
   selection, and bounded metadata fields;
3. the read service/API deterministically returns new strategy evidence without
   Provider/vector initialization;
4. the Timeline already renders dense/sparse/fused/rerank score slots only when
   their persisted values are non-null;
5. current Naive RAG behavior and audit linkage remain fully regressed.

`P4-M3-S1～S3` may begin. This is an entry decision, not an implementation of
M3 behavior.

## Git Handoff

The working tree is intentionally left unstaged for the user's manual commit.
Suggested commit message:

```text
fix(observability): expose trace run metrics
```
