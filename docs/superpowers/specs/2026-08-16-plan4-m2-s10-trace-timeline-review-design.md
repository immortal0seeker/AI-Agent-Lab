# Plan 4 M2 S10 Trace Timeline Review Design

## Context

`P4-M2-S1～S9` has delivered the Trace foundation integrations, persisted LLM
and Naive RAG evidence, bounded read-only Trace APIs, and the responsive Trace
Timeline workspace. `P4-M2-S10` closes the milestone by publishing the
dedicated usage document, independently reviewing the complete M2 contract,
repairing current documentation drift, and proving the M3 entry gate.

The batch starts on `main` at
`be7ee17105ebd8421874e45eba565e1545b086e3`, with `origin/main` at the same
commit and a clean, unstaged working tree.

The repository review policy and the user's current decision are authoritative:
Codex self-review is the only review gate. This batch will not request, run,
wait for, cite, or depend on Claude Code or another external reviewer.

## Goal

Close Plan 4 M2 with complete Trace Timeline usage documentation, a
Codex-only consolidated M2 review, fresh risk-matched verification, and an
explicit decision on whether `P4-M3-S1～S3` may begin.

## Scope

### In Scope

- Create `docs/31-trace-timeline.md` as the operator/developer guide for the
  implemented Trace list/detail API and Timeline workspace.
- Create `docs/reviews/2026-08-16-plan4-m2-final-review.md` covering
  `P4-M2-S1～S10` and the complete M2 contract.
- Reconcile README, Chinese README, architecture, CHANGELOG, and Plan 4
  execution status with the completed M2 boundary.
- Replace stale Claude review instructions throughout the active Plan 4
  execution table with the repository's Codex-only review policy, including
  milestone rows, Step rows, and the dedicated review-node section.
- Audit M2 code and tests for correctness, transaction ownership, safe error
  persistence, bounded read queries, Trace/candidate ordering, deep links,
  async stale-response protection, source identity, and Plan boundaries.
- If a reproducible Critical or Important M2 defect is found, fix it in this
  batch with a failing test first, minimal implementation, documentation
  synchronization, and fresh regression.
- Run fresh backend, migration, frontend, browser, documentation, security,
  artifact, and Git verification before closing the milestone.

### Out Of Scope

- `P4-M3-S1` or any Retrieval Strategy runtime.
- Metadata filtering, Qdrant filter builders, BM25, Hybrid Search, RRF,
  Parent-Child retrieval, Query Rewrite, reranking, or evaluation.
- Agent/Tool Trace integration, multi-Step cost aggregation, cancellation
  policy, or Prompt-construction failure persistence.
- Memory, Agent Runtime v2, Planner, Human Approval, MCP, OCR, multimodal, or
  any Plan 5/6 capability.
- Real paid Provider calls, real network Tools, real credentials, or user data.
- Git stage, commit, push, branch, worktree, merge, rebase, or tag operations.

## Documentation Architecture

### Trace Timeline Usage Guide

`docs/31-trace-timeline.md` will be the concise operational entry point rather
than a duplicate of the persistence specification in
`docs/30-trace-observability.md`. It will cover:

1. implemented scope and prerequisites;
2. opening the Trace workspace and using `?workspace=trace&run=<uuid>`;
3. list/detail API contracts, limits, deterministic ordering, and errors;
4. how to read Run status, correlations, Step order, metadata, retrieval Runs,
   candidate scores, selection, and source IDs;
5. representative RAG Query, RAG Chat, success, failure, and zero-hit flows;
6. privacy and bounded-persistence rules;
7. troubleshooting for empty lists, missing Runs, missing retrieval evidence,
   and failed API/health states;
8. desktop/mobile acceptance screenshots and verification references;
9. explicit M2 limitations and later Plan 4 ownership.

The guide will link to the canonical foundation document, API/test sources,
formal screenshots, and the M2 final review. It will not claim Agent/Tool Trace,
Advanced RAG, rerank, evaluation, full Prompt reconstruction, full source text,
or vector payload replay.

### Consolidated M2 Review

`docs/reviews/2026-08-16-plan4-m2-final-review.md` will contain:

- decision and Git baseline;
- S1～S10 acceptance matrix;
- delivered architecture and stable contracts;
- fresh verification evidence;
- findings classified as must fix, fix later, recorded limitation, or not
  applicable;
- security and Plan-boundary review;
- Codex-only self-review conclusion;
- M3 entry gate and Git handoff.

Earlier S1～S3, S4～S6, and S7～S9 reviews remain detailed evidence, but they do
not replace the independent milestone-level review.

### Project Status Reconciliation

- README and README_CN will link the usage guide and M2 final review and state
  that M2 is complete through S10.
- `docs/01-architecture.md` will correct stale statements that still describe
  the already-implemented Trace API/Timeline as future work.
- CHANGELOG will record the published Trace Timeline guide and M2 closeout
  without creating a release entry.
- The Plan 4 execution table will mark Batch 7/S10 complete and make every
  review instruction Codex-only. Historical source-plan requirements remain
  otherwise unchanged.

## Audit And Repair Policy

The review begins read-only. Suspected implementation defects must be
reproduced before editing code. A Critical or Important issue owned by M2 is a
must-fix and follows strict TDD: failing focused test, minimal fix, focused
GREEN, then full regression. Minor issues are classified and documented unless
they are trivial, adjacent, and safer to fix immediately. Later-milestone
capabilities are never implemented as review repairs.

Routes must remain thin, SQLite remains the primary audit database, Provider
details stay outside business services, and Trace writes remain owned by the
calling transaction. No test may initialize a paid Provider or depend on a
real Qdrant collection for the SQLite-only Trace read surface.

## Verification Design

Fresh completion evidence will include:

- focused M2 Trace backend tests;
- full backend pytest from a system-temporary working directory, SQLite URL,
  and document-storage root, followed by `pip check`;
- temporary SQLite upgrade, `current --check-heads`, `alembic check`, one-step
  downgrade, re-upgrade, and final head verification;
- frontend typecheck, full Vitest, and production build;
- headed Trace Timeline acceptance at 1440×900 and 390×844 using synthetic
  records only, covering deep links, failure state, ordered Steps/candidates,
  metadata expansion, request/console failures, and horizontal overflow;
- Markdown/local-link validation;
- high-confidence secret/private-key, generated database/artifact, external
  review reference, network Tool, and later-Plan runtime scans;
- `git diff --check`, staged-path count, branch/HEAD/origin/tag, and final
  status verification.

Docker/Qdrant live smoke is not required unless the audit changes a vector
adapter, collection/filter/payload contract, or retrieval runtime. Browser
screenshots will be replaced only if fresh acceptance reveals a material visual
change; otherwise the sanitized S7～S9 assets remain canonical.

## Completion Criteria

S10 is complete only when:

- the Trace Timeline guide and M2 final review exist and have no missing local
  links;
- all current-facing status documents agree that M2 is complete through S10;
- no active Plan 4 instruction asks for Claude review;
- all reproducible M2 must-fix findings are resolved;
- fresh verification and Codex self-review have no blocking issue;
- the working tree contains only S10-related changes and staged paths remain
  zero;
- the final review explicitly decides whether `P4-M3-S1～S3` may begin.

## Suggested Manual Commit

```text
fix(observability): expose trace run metrics
```
