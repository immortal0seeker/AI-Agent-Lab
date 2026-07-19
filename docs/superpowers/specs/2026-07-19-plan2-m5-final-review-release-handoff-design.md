# Plan 2 M5 Final Review And Release Handoff Design

## Scope

This design covers only `P2-M5-S7～S8`:

- review the complete Plan 2 candidate from `v0.1.0` through the current HEAD;
- fix only release-blocking Plan 2 defects that can be reproduced with local mocks or temporary data;
- record the final Codex review and the five Plan 3 bridge decisions;
- prepare an auditable `v0.2.0` release-commit and tag handoff.

It does not implement Plan 3, change the SQLite-first architecture, enable a real Provider, add `web_fetch`, or introduce any deferred Agent capability. The user owns staging, committing, pushing, and tag creation, so the repository must continue to report `v0.1.0` as the latest existing tag until the user creates `v0.2.0` on the verified release commit.

## Acceptance Evidence Matrix

| Step | Acceptance requirement | Existing evidence | Final-review action | Completion rule |
|---|---|---|---|---|
| S7 | Review the complete Plan 2 implementation and fix blockers | M1～M5 batch records, 451 backend tests, 79 frontend tests, mock browser screenshots | Inspect the complete `v0.1.0..HEAD` runtime surface, run fresh full verification, classify every finding, and use TDD for any runtime fix | No unresolved must-fix finding; backend, frontend, migration, docs, security, and Plan-boundary gates pass |
| S8 | Record the Plan 3 bridge | The execution table already lists five bridge contracts as done | Revalidate Registry extensibility, ToolResult shape, ToolCall ownership, file-tool security, and bounded Agent failure behavior against code/tests/docs | All five bridge items have current evidence and no Plan 3 runtime is added |
| S8 | Prepare the `v0.2.0` release boundary | S4～S6 produced release-candidate docs, screenshots, and `[Unreleased]` notes | Add the formal final-review record and update current-stage/release handoff text | Release commit is ready, but tag remains explicitly pending until the user creates it |
| S8 | Create and verify `v0.2.0` tag | Only `v0.1.0` currently exists | Do not mutate Git; provide exact manual commit/tag commands after a clean verification handoff | This item and Plan 2 remain pending until `git tag --list v0.2.0` and the peeled tag commit are verified in a later turn |

## Review Method

The review is evidence-first. It maps every Plan 2 final acceptance item to its production owner, focused tests, public documentation, and fresh full-suite result. It inspects the route-to-service boundary, Provider-neutral Tool contracts, persistence ownership, path security, failure redaction, frontend state transitions, migration consistency, and Plan 1 regressions. Automated tests use only Mock Providers/Tools, controlled temporary workspaces, and newly created temporary SQLite databases.

No test or production code is changed merely to increase counts. If review exposes a real defect, one focused regression must fail for the reproduced reason before the smallest fix is applied, followed by focused and full verification. Documentation-only truth corrections do not require a synthetic failing test.

## Release And Tag Boundary

The final review record will live at `docs/reviews/2026-07-19-plan2-v0.2.0-final-review.md`. README, CHANGELOG, architecture, the Plan 2 release document, and the execution table may describe the candidate as final-review-passed and ready for the release commit. They must also state that the latest existing tag is still `v0.1.0`, that S8 tag creation is pending user action, and that Plan 3 cannot start until the tag points at the verified release commit.

The user handoff sequence is:

1. review the unstaged S7～S8 diff;
2. manually stage and commit it with the suggested release message;
3. create annotated tag `v0.2.0` on that release commit;
4. return for a clean-worktree/tag-target verification before beginning `P3-M1-S1`.

## Fixed Limitations

The accepted Plan 2 limitations remain release facts: synchronous non-streaming Agent execution, sequential Tool Calls, no run list/polling/cancel/resume/retry, no strict persisted ToolCall sequence, no Agent-linked `LLMCall` usage/cost, character-based observation compaction, tracked example model with `supports_tools=false`, mock-only Provider acceptance, deferred `web_fetch`, and editable-source-only Registry packaging. These are not release blockers and are not implemented in this batch.
