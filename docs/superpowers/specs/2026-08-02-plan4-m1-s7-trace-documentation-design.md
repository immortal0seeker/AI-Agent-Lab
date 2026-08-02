# Plan 4 M1 S7 Trace Documentation And Review Design

## Status And Scope

This design covers only `P4-M1-S7`, the closing documentation and Codex review
step for the Plan 4 M1 Trace foundation.

The batch documents the already implemented and verified S1-S6 contracts. It
does not add or change production code, database schema, migrations, API
routes, frontend behavior, Chat/RAG/Agent Trace hooks, Advanced RAG,
reranking, evaluation, or Plan 5 runtime behavior.

The formal document is current-fact documentation. Planned M2 API, Timeline,
and runtime integrations are identified only as deferred boundaries and are
never presented as available behavior.

## Acceptance Matrix

| Requirement | Deliverable | Verification |
|---|---|---|
| Explain TraceRun and TraceStep fields and ownership | `docs/30-trace-observability.md` model/field reference | Compare against ORM, schemas, enums, and migration `20260802_0008` |
| Explain lifecycle and transaction semantics | Formal lifecycle, Service, ContextVar, error, and caller-owned transaction sections | Compare against Trace Service/Context tests and source |
| Explain token/cost/latency metadata | Formal usage helper and JSON-safe metadata section | Compare against canonical helper and Mock persistence test |
| Keep public project status accurate | README/README_CN, architecture, and Plan 4 execution-table synchronization | Text consistency and local-link checks |
| Complete M1 with Codex-only review | One consolidated M1 final review | Fresh focused/full backend, migration, dependency, hygiene, and Git evidence |

## Alternatives Considered

### 1. Standalone Current-Fact Contract Document - Chosen

Create one durable formal reference that a reader can understand without
opening implementation specs or review logs. Synchronize the high-level
project documents and close M1 with a fresh consolidated Codex review. This
meets S7 directly and keeps planned behavior unmistakably separate.

### 2. Spec And Review Index Only

An index would minimize repeated prose, but the existing specs are
implementation-decision records rather than a stable user/developer contract.
It would not independently explain fields, lifecycle, transactions, or current
limitations, so it does not satisfy S7.

### 3. Future-Facing API And Timeline Guide

Including planned endpoints or frontend examples could help M2 planning, but
it would blur the boundary between current and future behavior. M2 owns those
contracts and will document them after implementation.

## Chosen Documentation Design

### 1. Formal Trace Foundation Document

`docs/30-trace-observability.md` is the canonical M1 contract and contains:

1. current scope and explicit non-capabilities;
2. component map from enums/schemas/models/migration through Service, Context,
   and usage helper;
3. TraceRun field groups, correlations, ownership, and audit-preserving delete
   behavior;
4. TraceStep fields, deterministic order, ownership, and cascade behavior;
5. exact run/step enums and statuses;
6. lifecycle operations and invalid-transition behavior;
7. caller-owned transaction semantics, including rollback behavior and how a
   later product flow may deliberately persist a normalized failure;
8. ContextVar binding, nesting, copied-context isolation, and automatic step
   success/failure behavior;
9. token/cost/latency calculation and JSON-safe metadata shape;
10. security boundaries, concurrency limitation, and deferred M2 behavior;
11. code/test/migration links for verification.

The document may use compact text flows and tables. It does not invent a
public API, runtime configuration option, cancellation state transition,
automatic run aggregation policy, or frontend representation.

### 2. Project Status Synchronization

`README.md` and `README_CN.md` are updated symmetrically:

- current stage becomes Plan 4 M1 complete through S7;
- the stale statement that Plan 4 has not started is removed;
- the documentation index links to the formal Trace document and M1 final
  review;
- limitations distinguish available persistence/lifecycle infrastructure from
  absent runtime integration, API, and UI;
- the roadmap identifies the Trace foundation as complete rather than in
  progress.

`docs/01-architecture.md` adds `observability/` to the repository/layer map,
updates the Plan 4 current-stage summary, and replaces the stale S1-S3 note
that Service/Context are still next work. It links to the formal Trace
document rather than duplicating every operational detail.

The Plan 4 execution table marks only Batch 3 / S7 complete. Its M1 review
wording is corrected to the repository's current Codex-only policy. Later
Plan 4 batches remain untouched and incomplete.

`CHANGELOG.md` already records the complete S1-S6 behavior. S7 changes it only
if a concise documentation-reference adjustment is necessary; it does not add
a second feature claim for documentation alone.

### 3. Consolidated M1 Review

`docs/reviews/2026-08-02-plan4-m1-final-review.md` consolidates S1-S7 without
copying every prior log. It records:

- starting and ending Git baselines;
- S1-S7 acceptance mapping;
- fresh verification results;
- fixed findings and recorded limitations from both implementation batches;
- current security/transaction/concurrency boundaries;
- explicit M2 entry decision and prerequisites;
- Codex-only self-review conclusion and suggested manual commit message.

The earlier S1-S3 and S4-S6 reviews remain immutable supporting evidence and
are linked from the final review.

## Verification Strategy

Because S7 changes documentation only, it does not use TDD. Verification is
risk-matched to the whole M1 foundation being closed:

1. run all Trace model/schema/type/migration/service/context/usage tests plus
   Chat/RAG compatibility tests;
2. run the complete backend suite from a system-temporary working directory
   with explicit temporary SQLite/storage paths;
3. run `pip check`;
4. exercise the temporary SQLite Alembic lifecycle through head
   `20260802_0008`: upgrade, current/check-heads, autogenerate drift check,
   downgrade to `20260801_0007`, and re-upgrade;
5. validate all tracked/new Markdown local links and images;
6. scan changed text for high-confidence secrets/private keys and inspect
   changed paths for generated artifacts, network Tool runtime, M2/Plan 5
   implementation, and user-database changes;
7. run `git diff --check`, confirm zero staged paths, and recheck branch, HEAD,
   origin/main, and relevant tags.

Frontend typecheck/Vitest/build, browser replay, Docker, and Qdrant are not
rerun because S7 changes no frontend, route, active runtime, retrieval,
payload, vector-store, or Compose behavior. This decision is recorded in the
final review.

## Review Policy

Codex self-review is the only review gate. No Claude Code, Fable, or other
external review is requested, run, awaited, or cited. Outdated planning-table
language for this S7/M1 gate is synchronized to that policy.

Findings are classified as must fix, fix later, recorded limitation, or not
applicable. Any factual documentation mismatch is a must-fix in this batch and
is corrected before completion.

## Completion Boundary

S7 is complete when the formal Trace foundation document independently
describes the implemented fields and lifecycle, all project-status documents
agree, the consolidated M1 review contains fresh evidence, verification and
link/hygiene/Git gates pass, and Codex self-review finds no remaining
must-fix.

Completion closes Plan 4 M1 only. It authorizes entry to `P4-M2-S1-S3` after
the user manually commits S7, but it does not implement or activate any M2
behavior.
