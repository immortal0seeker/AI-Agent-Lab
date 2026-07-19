# Plan 2 M5 Frontend Checks And Release Materials Design

## Scope

This design covers only `P2-M5-S4` through `P2-M5-S6`:

- refresh the automated and browser evidence for the existing Agent/ToolCall UI;
- synchronize README and Plan 2 documentation with the already implemented M4 UI and M5 test hardening;
- prepare sanitized screenshots, changelog entries, and current limitations for the future `v0.2.0` release.

It does not perform the `P2-M5-S7` full Plan review, create the `v0.2.0` tag from `P2-M5-S8`, or begin Plan 3. The current release remains `v0.1.0` until the user completes those later steps.

## Acceptance Gap Matrix

| Step | Acceptance requirement | Existing evidence | Current gap | Minimal addition |
|---|---|---|---|---|
| S4 | Frontend ToolCall display check | M4 component tests and temporary mocked desktop/mobile browser acceptance | No fresh M5 check or committed release asset | Re-run typecheck, full Vitest, production build, and local mocked desktop/mobile browser checks; change runtime code only if a real defect is reproduced |
| S5 | README and Plan 2 documents explain startup, Tool boundaries, and current Agent behavior | README/README_CN and `docs/12-agent-api.md` describe the M4 UI | README stage/next-batch text is stale; `docs/10` and `docs/11` still say the API/UI is future work | Update the bilingual README, `docs/10`, `docs/11`, and directly related overview/architecture stage text without claiming a release tag |
| S6 | Screenshot, CHANGELOG, and current limitations make the `v0.2.0` boundary clear | Only Plan 1 screenshots are committed; Unreleased changelog covers M4 features | No sanitized Plan 2 release-candidate screenshots or consolidated release-candidate document | Add desktop/mobile Agent ToolCall screenshots, a Plan 2 release-candidate document, changelog notes, and explicit limitations |

## Browser Verification And Screenshot Contract

The frontend runs only on the local Vite server and calls a temporary Python standard-library Mock API bound to `127.0.0.1:8000`. The Mock returns fixed health, model, AgentRun, and ToolCall payloads without importing the project backend or opening a database. Playwright drives only this local flow. No backend user database, `.env`, credential, real Provider, paid API, or network Tool is used.

The completed mock run uses fixed synthetic UUIDs and demonstrates:

- one tools-capable Mock model;
- the goal `Read README.md and summarize the workspace structure.`;
- a completed final answer;
- a successful `read_file` ToolCall with `README.md` arguments, bounded result text, 25 ms latency, and visible Provider/database IDs;
- visible AgentRun and Conversation IDs;
- no horizontal overflow at 1280×900 and 390×844.

Playwright first writes temporary captures under `output/playwright/`. The responsive checks use exact 1280×900 and 390×844 viewports; the documentation assets retain the same 1280px and 390px layout breakpoints with taller canvases so the complete ToolCall audit is visible. After visual inspection, the sanitized final images are copied to:

- `docs/assets/plan2/agent-tool-call-desktop.png`
- `docs/assets/plan2/agent-tool-call-mobile.png`

The temporary Mock script, browser profiles, logs, captures, Vite process, and Mock API process are removed after verification. Only the two reviewed images remain tracked candidates.

## Documentation Structure

`README.md` and `README_CN.md` remain the startup entry point. They state that Plan 2 is complete only through M5-S6, that S7-S8 are still pending, that the tracked example model has Tool support disabled, and that local operators must configure a tools-capable model and Provider without committing credentials.

`docs/10-tool-calling-design.md` owns Tool/Registry/security/Provider boundaries and the current UI surface. `docs/11-simple-agent-loop.md` owns loop behavior, API integration, UI visibility, and runtime limitations. `docs/13-plan-2-basic-agent.md` becomes the consolidated release-candidate boundary and embeds the sanitized screenshots. `docs/00-project-overview.md` and `docs/01-architecture.md` receive only stage/current-fact corrections. `CHANGELOG.md` stays under `[Unreleased]`; it must not invent a `0.2.0` release date.

## Verification And Review Boundary

The batch reruns backend pytest and dependency checks, frontend typecheck/full Vitest/build, and Alembic checks against a newly created temporary SQLite database. Documentation checks cover Markdown links/images, secret-like values, generated artifacts, `web_fetch` runtime absence, later-Plan surfaces, Git staging, and whitespace.

Codex self-review is the only review gate. Findings are classified as must fix, later Step, accepted limitation, or not applicable. Any actual UI defect found in S4 receives a focused failing regression test before the smallest production fix; otherwise no frontend runtime or test file is changed merely to increase test counts.
