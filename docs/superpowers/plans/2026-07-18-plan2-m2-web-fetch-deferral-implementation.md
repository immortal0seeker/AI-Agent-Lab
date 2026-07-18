# Plan 2 M2 web_fetch Deferral Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `P2-M2-S7` by documenting the approved `web_fetch` deferral, closing Plan 2 M2 with `read_file` and `list_dir`, and recording fresh M2 review evidence.

**Architecture:** Make documentation-only changes. Preserve the executable Tool Registry exactly as shipped in S1-S6, expose no network Tool surface, and route the next batch to Provider Tool Calling rather than adding partial SSRF defenses.

**Tech Stack:** Markdown documentation, existing Python 3.11/FastAPI backend verification, existing React/TypeScript frontend verification, Git read-only checks.

## Global Constraints

- Scope is exactly `P2-M2-S7`.
- The accepted decision is explicit deferral; do not implement `web_fetch`.
- Do not create `web_fetch.py`, `WebFetchTool`, URL/network security helpers, tests for nonexistent behavior, dependencies, configuration, APIs, or frontend UI.
- Do not register or export a `web_fetch` schema or name.
- Plan 2 M2 closes with `read_file` and `list_dir` only.
- The next batch is `P2-M3-S1` through `P2-M3-S3`.
- Provider tool calling and the Agent Loop remain unimplemented in this Step.
- Do not make real network requests, resolve live hostnames for feature testing, call a real Provider, read real secrets, or touch the user's SQLite database.
- Do not modify `CHANGELOG.md`; it contains released `v0.1.0` history only.
- Do not stage, commit, push, or create tags; the user performs Git mutations manually.
- Do not use subagents unless the user explicitly changes the current restriction; execute inline with `executing-plans`.

## File Map

- Modify `README.md`: close M2, state the deferral, and point to M3 S1-S3.
- Modify `README_CN.md`: mirror the English current-stage facts in Chinese.
- Modify `docs/00-project-overview.md`: record S7 completion and the M2 minimum Tool set.
- Modify `docs/01-architecture.md`: keep the architecture limited to two local read-only builtins and record the network Tool boundary.
- Modify `docs/10-tool-calling-design.md`: replace optional evaluation wording with the accepted deferral and rationale.
- Modify `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`: mark Batch 6/S7 complete and append the S7/M2 review record.
- Do not modify backend/frontend source, tests, dependencies, environment examples, migrations, or `CHANGELOG.md`.

---

### Task 1: Close M2 In User-Facing And Architecture Documentation

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/10-tool-calling-design.md`

**Interfaces:**
- Consumes: the approved S7 deferral spec and implemented `read_file`/`list_dir` facts.
- Produces: one consistent current-stage statement with no executable `web_fetch` claim.

- [ ] **Step 1: Update the English README current-stage block**

Replace the current Plan 2 block in `README.md` with text containing these exact facts:

```markdown
Current development stage: Plan 2 M2 is complete. Completed Plan 2 scope:
`P2-M1-S1` through `P2-M2-S7`.

The M1 foundation includes Tool and ToolResult contracts, ToolCall transport
schemas, an ordered Tool Registry, Draft 2020-12 argument validation, read-only
path policy, and AgentRun/ToolCall ORM models with an Alembic migration. M2
adds the two registered read-only builtins `read_file` and `list_dir`, with
bounded I/O, workspace-relative path policy, sensitive-name filtering, safe
failures, and mocked regression coverage. `web_fetch` was evaluated in
`P2-M2-S7` and explicitly deferred because a trustworthy network Tool requires
a complete SSRF, DNS/redirect, timeout, response-size, content-type, and text-
extraction boundary. No `web_fetch` Tool or schema is implemented or exposed.
Provider tool calling, an Agent Loop, Agent APIs, and frontend Agent/ToolCall
views are not yet implemented.

Next batch: `P2-M3-S1` through `P2-M3-S3`.
```

- [ ] **Step 2: Update the Chinese README with equivalent facts**

Replace the matching current-stage block in `README_CN.md` with:

```markdown
当前开发阶段：Plan 2 M2 已完成。已完成的 Plan 2 范围为 `P2-M1-S1` 到
`P2-M2-S7`。

M1 地基包括 Tool 与 ToolResult 契约、ToolCall 传输 schema、有序 Tool
Registry、Draft 2020-12 参数校验、只读路径策略，以及 AgentRun/ToolCall ORM
模型与 Alembic 迁移。M2 新增并注册 `read_file` 与 `list_dir` 两个只读内置
Tool，具备有界 I/O、工作区相对路径策略、敏感名称过滤、安全失败结果和 Mock
回归覆盖。`P2-M2-S7` 已完成 `web_fetch` 评估并明确延期：可信网络 Tool 需要
完整处理 SSRF、DNS/重定向、超时、响应大小、内容类型和正文提取边界。当前没有
实现、注册或暴露 `web_fetch` Tool/schema。Provider tool calling、Agent Loop、
Agent API 和前端 Agent/ToolCall 视图仍未实现。

下一批：`P2-M3-S1` 到 `P2-M3-S3`。
```

- [ ] **Step 3: Update project overview and architecture stage statements**

In `docs/00-project-overview.md`:

- change the current stage to “Plan 2 M2 is complete”;
- change completed Plan 2 scope to `P2-M2-S7`;
- state that the M2 executable set is `read_file` and `list_dir` only;
- state that `web_fetch` was evaluated and deferred with no Tool/schema surface;
- set the next batch to `P2-M3-S1` through `P2-M3-S3`.

In `docs/01-architecture.md`, replace the Plan 2 stage paragraph with:

```markdown
Plan 2 has completed `P2-M1-S1` through `P2-M2-S7`: Tool contracts,
Registry, validation, read-only path policy, AgentRun/ToolCall persistence, and
the executable `read_file` and `list_dir` builtins are available. `web_fetch`
was evaluated and deferred; no network Tool, Provider Tool Calling, or Agent
runtime behavior is implemented at this stage.
```

After the builtin data-flow section, add a short network boundary paragraph:

```markdown
`web_fetch` is intentionally absent from this architecture. A future
reassessment must define SSRF-safe address and redirect validation, DNS-
rebinding resistance, bounded streaming, content policy, text extraction,
safe errors, and mock acceptance coverage before exposing a network Tool.
```

- [ ] **Step 4: Record the accepted deferral in Tool Calling Design**

In `docs/10-tool-calling-design.md`:

- change current scope to `P2-M2-S1` through `P2-M2-S7`;
- state that M2 is complete with two read-only builtins;
- add a `web_fetch Deferral` section containing this decision:

```markdown
## web_fetch Deferral

`P2-M2-S7` evaluated `web_fetch` and explicitly deferred it. No
`web_fetch.py`, Tool/schema registration, URL helper, dependency, API, or UI is
implemented. A safe network Tool requires a complete scheme/port policy,
public-address and DNS-rebinding strategy, redirect revalidation, strict
timeouts, bounded streaming, content-type/decoding rules, safe HTML text
extraction, redacted errors, and mock coverage. Implementing a subset would
misrepresent the Tool as low risk.

The capability may be reassessed in Plan 4 or Plan 6, but neither Plan is
committed to this exact Tool shape. The active future Step must approve the
network permission and extraction contract before implementation.
```

- replace `optional web_fetch evaluation` in Deferred Work with
  `web_fetch reassessment, no earlier than Plan 4 or Plan 6`;
- identify Provider tool calling as the next Plan 2 implementation boundary.

- [ ] **Step 5: Check cross-document truth before updating acceptance status**

Run from the repository root:

```powershell
$files = @('README.md','README_CN.md','docs/00-project-overview.md','docs/01-architecture.md','docs/10-tool-calling-design.md')
Select-String -Path $files -Pattern 'P2-M2-S7|P2-M3-S1|web_fetch|Provider tool calling|Agent Loop' -Encoding utf8
Select-String -Path $files -Pattern 'Next batch: `P2-M2-S7`|下一批：仅 `P2-M2-S7`|optional `web_fetch` evaluation' -Encoding utf8
git diff --check
```

Expected: the first search shows the approved completed/deferred/next-batch facts; the stale-statement search prints no matches; diff check prints no errors.

---

### Task 2: Mark S7 Complete And Add The M2 Review Record

**Files:**
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: Task 1 documentation and the approved deferral decision.
- Produces: Batch 6 and S7 completion status plus an acceptance record that
  Task 3 verifies and finalizes with literal evidence.

- [ ] **Step 1: Mark only Batch 6 and S7 complete**

In the execution rhythm table, replace the Batch 6 row with:

```markdown
| Batch 6 | P2-M2-S7 | 可选实现 web_fetch 或明确延期记录 | Codex review M2 | 已完成（deferred） |
```

Replace the S7 row with:

```markdown
| P2-M2-S7 | 评估并处理 web_fetch：实现低风险版本或记录延期 | Codex | docs 延期与限制说明 | README / docs 明确未实现、延期原因和重评边界 | Codex review（done：deferred） |
```

Do not change any M3 or later row.

- [ ] **Step 2: Append the dated S7 decision record after S4-S6**

Append this section before the existing M2 completion commit suggestion:

```markdown
### P2-M2-S7 web_fetch 评估与 M2 review 记录（2026-07-18）

| 验收项 | 结果与证据 |
|---|---|
| 决策 | 采用计划允许的延期路径：Plan 2 不实现 `web_fetch`。M2 以 `read_file` 与 `list_dir` 两个只读内置 Tool 收口。 |
| 延期原因 | 可信网络 Tool 必须完整处理 scheme/port、SSRF、DNS 与重绑定、每次重定向复验、严格超时、有界流式响应、内容类型/解码、HTML 正文提取和安全错误；只实现其中一部分会形成误导性的“低风险”能力。 |
| 可执行边界 | 未创建 `web_fetch.py`、`WebFetchTool`、URL/network helper、依赖、配置、测试、Registry schema、API 或前端 UI；未发起真实网络请求或 Provider 调用。 |
| 重评边界 | 候选重评点为 Plan 4 或 Plan 6，但不承诺采用当前 Tool 形态；未来必须先批准完整网络权限、重定向/地址验证、提取和 Mock 验收契约。 |
| 全量验证 | Backend `271 passed, 1 warning`，`pip check` 通过；Frontend typecheck、8 files / 37 tests 和 production build（1804 modules transformed）通过。warning 仍是已知 Starlette TestClient/httpx 弃用提示。 |
| 文档与检查 | README/README_CN、项目概览、架构、Tool Calling 设计和执行表事实一致；记录最终本地 Markdown 链接、秘密模式、Git 可见生成物、无网络 Tool surface 和 diff 检查结果。 |
| Codex M2 review | 记录最终 self-review 分类与复验；确认未进入 Provider tools、Agent Loop、service/API/frontend Agent 视图或后续 Plan。未运行 Claude Code，除非用户另行明确要求。 |

**结论：** `P2-M2-S1`～`S7` 与 M2 已完成。下一批进入 `P2-M3-S1`～`S3`，本 Step 没有实现或暴露 `web_fetch`。

S7 建议 commit：

```text
docs(plan2): defer web fetch tool
```
```

After Task 3 finishes, replace the documentation/check and review descriptions with literal observed evidence. Do not invent counts or external review.

---

### Task 3: Fresh M2 Verification And Codex Self-Review

**Files:**
- Modify if evidence differs: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: all S7 documentation changes and the unchanged S1-S6 codebase.
- Produces: fresh M2 completion evidence and a clean handoff to M3 S1-S3.

- [ ] **Step 1: Load verification-before-completion before success claims**

Read `verification-before-completion/SKILL.md` completely and follow its evidence gate. Do not rely on S4-S6 test output.

- [ ] **Step 2: Prove no executable network Tool surface was added**

Run from the repository root:

```powershell
if (Test-Path -LiteralPath 'backend/app/tools/builtin/web_fetch.py') { throw 'web_fetch.py must not exist' }
$matches = Get-ChildItem -LiteralPath 'backend/app','backend/tests' -Recurse -File -Filter '*.py' | Select-String -Pattern 'WebFetchTool|name\s*=\s*["'']web_fetch["'']|register_tool\([^\r\n]*web_fetch' -Encoding utf8
if ($matches) { $matches; throw 'Executable web_fetch surface found' }
if (git diff --name-only -- backend/pyproject.toml backend/app backend/tests) { throw 'S7 must not change code, tests, or dependencies' }
'web_fetch_surface=absent'
```

Expected: `web_fetch_surface=absent`; no source/dependency diff.

- [ ] **Step 3: Run complete backend verification**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: `271 passed, 1 warning` and `No broken requirements found.` The warning must be only the known Starlette TestClient/httpx deprecation warning.

- [ ] **Step 4: Run complete frontend verification**

Run from `frontend/`:

```powershell
npm run typecheck
npm run test
npm run build
```

Expected: typecheck succeeds, 8 files / 37 tests pass, and production build succeeds with 1804 modules transformed. If the managed sandbox blocks `dist`, rerun only the build with the already approved build escalation.

- [ ] **Step 5: Check links, secrets, artifacts, boundaries, and Git diff**

Run from the repository root without opening ignored or sensitive paths:

```powershell
$ErrorActionPreference = 'Stop'
$changed = @(
  git -c core.quotepath=false diff --name-only
  git -c core.quotepath=false ls-files --others --exclude-standard
) | Sort-Object -Unique
$secretMatches = @(Select-String -LiteralPath $changed -Pattern 'sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,}|BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY' -Encoding utf8)
if ($secretMatches) { $secretMatches; throw 'Secret-like value found' }
git ls-files '*.pyc' '*.pyo'
git status --short --untracked-files=all -- '*.pyc' '*.pyo'
git diff --check
git diff --cached --check
git -c core.quotepath=false status --short --untracked-files=all
```

Run the local Markdown link check against root README files plus `docs/` and
`docs-plan/`:

```powershell
$markdownFiles = @(
  Get-Item -LiteralPath 'README.md','README_CN.md','AGENTS.md','AGENTS_CN.md'
  Get-ChildItem -LiteralPath 'docs','docs-plan' -Recurse -File -Filter '*.md'
)
$linkCount = 0
$missing = @()
foreach ($file in $markdownFiles) {
  $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding utf8
  foreach ($match in [regex]::Matches($text, '!?(?:\[[^\]]*\])\((?<target>[^)]+)\)')) {
    $target = $match.Groups['target'].Value.Trim().Trim('<','>')
    if ($target -match '^(https?://|mailto:|#)') { continue }
    $target = ($target -split '#',2)[0]
    if (-not $target) { continue }
    $linkCount++
    $resolved = [System.IO.Path]::GetFullPath(
      (Join-Path $file.DirectoryName ([uri]::UnescapeDataString($target)))
    )
    if (-not (Test-Path -LiteralPath $resolved)) {
      $missing += "$($file.FullName) -> $target"
    }
  }
}
"local_markdown_links=$linkCount"
if ($missing) { $missing; throw 'Missing local Markdown link target' }
```

Expected: every local target exists, secret matches are zero, no Python
artifact is tracked or Git-visible, and both diff checks pass.

- [ ] **Step 6: Run Codex M2 self-review**

Review the complete diff and classify findings as must fix, fix in later batch, record as limitation, or not applicable:

- only the approved spec/plan and six formal Markdown files changed;
- S7 is completed by deferral, not described as implemented;
- Registry exports remain exactly `read_file` and `list_dir`;
- no executable network code, live request, Provider integration, Agent Loop, API, frontend Agent UI, migration, or later-Plan feature appears;
- future reassessment language is non-binding and security-complete;
- M3 S1-S3 is the only next batch;
- `CHANGELOG.md` and release history are unchanged;
- no stage, commit, push, or tag operation occurred.

Fix every must-fix documentation inconsistency, then rerun link, secret, boundary, and diff checks.

- [ ] **Step 7: Finalize literal evidence and hand off without Git mutation**

Replace the acceptance record's documentation/review descriptions with the final observed counts and findings. Rerun:

```powershell
git diff --check
git status --short --untracked-files=all
```

Expected: no diff error and a documentation-only S7 scope. Do not commit. Hand off the S7 decision, verification evidence, Codex review, residual limitation, next batch `P2-M3-S1` through `P2-M3-S3`, and suggested manual commit message:

```text
docs(plan2): defer web fetch tool
```
