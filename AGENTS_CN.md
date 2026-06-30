# AGENTS.md

本文件是 AI Agent Lab / AI Engineering Workspace 的根级协作规范，适用于整个仓库。更深层目录的 `AGENTS.md` 可以补充局部规则。

根目录只写跨模块硬规则；模块细节放到子目录 `AGENTS.md`。

---

## 1. 项目目标

项目按 6 个计划递进：

- Plan 1: Project foundation + Basic Chat + LLM Providers
- Plan 2: Tool Calling + Simple Agent Loop
- Plan 3: Knowledge Base + Document Ingestion + Naive RAG
- Plan 4: Trace + Advanced RAG + Rerank + Evaluation
- Plan 5: Memory + Context Engine + Agent Runtime + Human Approval
- Plan 6: MCP + Voice + Vision + Desktop

目标不是堆 Demo，而是构建可观测、可评测、可扩展、可日常使用的 AI Engineering Workspace。

---

## 2. 执行流程

默认按固定小循环推进：

1. 领取连续 1～3 个 Step。
   - 只做用户指定范围内的 Step。
   - 不提前实现后续 Plan 能力。
2. Codex / Cursor 实现。
   - 按当前 Step 的交付物实现。
   - 保持 diff 范围干净。
   - 必要代码注释使用中文。
3. 跑对应验证。
   - 后端：单元测试、API 测试、启动验证或接口检查。
   - 前端：TypeScript 检查、构建、页面 smoke 或手测。
   - 文档/配置：检查链接、路径、secret 和 `git status`。
4. Codex 自审。
   - 检查是否只改了本批 Step 相关文件。
   - 检查是否跨 Plan。
   - 检查是否有 secret 泄漏。
   - 检查测试/验证证据是否充分。
   - 检查 README / docs / env example 是否需要同步。
   - 明确告诉用户：本批是否需要 Claude Code 复审。
5. 判断是否需要 Claude Code 复审。
   - 如果不需要 Claude Code 复审，继续修复和重新验证。
   - 如果需要 Claude Code 复审，暂停进入下一批 Step，等待复审结果。
6. 按审核意见修复。
   - 必须修：当前批次内修复。
   - 后续批次修：记录到后续 Step 或限制说明。
   - 记录为限制：写入 docs / README / review 记录。
   - 不适用：说明原因。
7. 重新验证。
   - 修复后重新跑验证。
   - 如仍有问题，重复 4～7。
   - 直到测试、验证、自审都没有阻塞问题。
8. 完成本批。
   - 给出变更摘要。
   - 给出验证结果。
   - 给出 Codex review 结论。
   - 说明是否需要 Claude Code 复审。
   - 给出遗留风险或限制。
   - 给出下一批 Step 建议。
   - 给出建议 commit message，但实际 commit 由用户手动创建，除非用户明确要求 Codex commit。

用户指定 `P1-M1-S1～P1-M1-S3` 这类范围时，只做该范围。

---

## 3. 计划边界

不要提前实现后续计划能力。

- Plan 1 不做 Tool Calling、RAG、Memory、MCP、Voice、Vision、Desktop。
- Plan 2 不做 RAG、Embedding、Memory、MCP、Shell Tool、写文件工具。
- Plan 3 不做 Advanced RAG、Rerank、Evaluation、Memory、OCR、多模态。
- Plan 4 不做 Memory、Agent Runtime v2、Planner、Human Approval、MCP、多模态。
- Plan 5 不做 MCP、Voice、Vision、Desktop、多 Agent、Browser Use、Computer Use。
- Plan 6 不做多 Agent、A2A、Browser Use、Computer Use、插件市场、移动端。

如果后续能力看起来必要，记录为桥接项，不要直接实现。

---

## 4. 架构原则

优先小模块、清晰边界、可独立测试。

每个重要模块都要能回答：它负责什么、依赖什么、产出什么、谁会调用它、如何测试它。

API route 保持薄层：`Route -> schema validation -> service -> response schema`。

业务逻辑放 service，不放 route。Provider 细节放 provider adapter，不泄漏到业务层。

不要提前创建尚未进入当前计划的未来目录。

代码注释默认使用中文，因为本项目主要用于学习。只有在说明非显而易见的意图、边界、取舍或学习点时才写注释，不要把自解释代码翻译成注释。

---

## 5. 目录预期

仓库会逐步形成：

- `backend/`
- `frontend/`
- `desktop/`
- `docs/`
- `scripts/`
- `tests/`
- `README.md`
- `CHANGELOG.md`
- `AGENTS.md`

后端会逐步形成：`api/`、`core/`、`db/`、`models/`、`schemas/`、`providers/`、`tools/`、`rag/`、`observability/`、`memory/`、`context_engine/`、`agents/`、`mcp/`、`voice/`、`multimodal/`、`desktop/`。

---

## 6. 后端规则

使用 FastAPI。

数据库、schema、service、API、测试必须同步演进。

改数据库字段时，同时更新 ORM model、migration、Pydantic schema、service tests、API tests；如果用户可见，也更新 docs。

LLM / Embedding / Rerank / STT / TTS / OCR / Vision / MCP Provider 失败不能导致服务崩溃。返回可读、可测试、可追踪的错误。

---

## 7. 前端规则

使用 React + TypeScript。

- `frontend/src/api/`: API 封装。
- `frontend/src/types/`: 共享类型。
- `frontend/src/pages/`: 页面。
- `frontend/src/components/`: 功能组件。

这是工程工作台，不是营销页面。界面应安静、密集、可扫描。

异步流程必须有 loading、empty、error、success/result 状态。

Trace、Tool Call、Approval、Agent Run 页面必须保留可追踪 ID。

---

## 8. 测试规则

每批 Step 提交前必须验证。

优先 mock，不依赖真实付费 API。LLM、Embedding、Rerank、STT、TTS、OCR、Vision、MCP 都应支持 mock 测试。

后端至少覆盖 pure logic unit tests、service state tests、API tests、error-path tests。

前端至少覆盖 TypeScript check、页面 smoke 或手测、关键流程截图或记录。

没有新鲜验证结果，不要声称完成。

---

## 9. Review 规则

每批 Step 后做 Codex review。

这些位置优先用 Claude Code 复审：数据库模型、Provider 抽象、RAG / ranking、Trace / Evaluation、Memory 写入策略、Context Engine、Agent Runtime 状态机、Human Approval、MCP Permission、Desktop 本地文件权限、release candidate。

Review 意见必须分类为：必须修、后续批次修、记录为限制、不适用并说明原因。

修复后重新测试。

---

## 10. 安全规则

真实 secret 不能提交。

不要把真实值写入 `.env.example`、README、docs、tests、fixtures、screenshots、Trace、logs、frontend state、seed data。

API key、token、MCP env secret、Provider credential 只能通过本地未跟踪 `.env`、环境变量、secret reference 或本地加密配置传递。

不要明文入库，不要写日志，不要在前端响应中暴露。UI 展示必须脱敏。

---

## 11. Tool 与本地权限

默认只读。

写文件、删文件、执行命令、外部付费 API、高风险 MCP、本地敏感路径访问都必须有风险判断。

一旦 Human Approval 可用，高风险动作必须审批。

`retry` 不得绕过审批。`resume` 不得绕过审批。MCP tool call 不得绕过权限策略。本地文件访问不得绕过 `trusted_paths`。

禁止路径穿越。禁止读取 `.env`、SSH key、浏览器 profile、系统凭据存储。

---

## 12. Agent Runtime 规则

Agent 执行必须可复盘。

重要记录包括 `agent_run`、`agent_step`、`tool_call`、`approval_request`、`trace_run`、`trace_step`、cost / latency metadata。

状态机变化必须测试。不要随意增加 runtime state。

新增状态时，同步更新 enum、transition rules、schema、API、frontend badge、tests、docs。

Human Approval 是安全边界，不是普通 UI。

---

## 13. RAG 与 Evaluation 规则

RAG 必须保留 source metadata。

回答应可追踪：检索了哪个 knowledge base、命中了哪些 document / chunk、使用了什么 retrieval strategy、选择了哪些 source、对应哪个 trace_run。

Evaluation 要可复现。不要只靠人工感觉判断检索质量。

---

## 14. 文档规则

用户可见或运维可见行为变化时，更新相关文档：README、CHANGELOG、docs、`.env.example`、active plan notes、截图或手测记录。

文档不能声称未实现的能力。延期能力要明确写成限制。

文档目录边界：

- `docs-plan/`：计划源文档，记录总路线、各 Plan、执行步骤表和验收标准。必须提交，不放入 `.gitignore`。
- `docs/`：正式项目文档，记录已实现或当前阶段正在交付的架构、接口、启动说明、验收截图和复盘材料。必须提交，不放入 `.gitignore`。
- `docs-local/`：本地草稿、未脱敏材料、临时 review、调试记录、私有截图和敏感上下文。必须放入 `.gitignore`，不得提交。

如果 `docs-local/` 中的内容需要沉淀为项目资产，必须先脱敏、整理，并移动到 `docs/` 或 `docs-plan/` 的合适位置。

---

## 15. Commit 规则

按已验证批次准备 commit，不按零碎编辑 commit。实际 commit 默认由用户手动创建，除非用户明确要求 Codex commit。

建议 commit 前检查：diff 范围是否只覆盖本批 Step、测试是否通过、是否误提交 secret、文档是否同步、是否误改无关文件。

提交信息示例：

- `feat(chat): add streaming message persistence`
- `fix(provider): normalize timeout errors`
- `test(rag): cover chunk metadata filtering`
- `docs(plan1): record v0.1.0 setup flow`
- `chore(release): tag v0.1.0`

---

## 16. 子目录 AGENTS.md 策略

二级 `AGENTS.md` 建议覆盖：`backend/`、`frontend/`、`docs/`、`desktop/`、`backend/app/providers/`、`backend/app/tools/`、`backend/app/rag/`、`backend/app/observability/`、`backend/app/memory/`、`backend/app/context_engine/`、`backend/app/agents/`、`backend/app/mcp/`、`backend/app/voice/`、`backend/app/multimodal/`。

三级只给高风险模块：`backend/app/agents/runtime/`、`backend/app/agents/approval/`、`backend/app/rag/strategies/`、`backend/app/providers/*/`、`backend/app/desktop/`。

不要写四级 `AGENTS.md`，除非用户明确要求。

---

## 17. 停止条件

遇到这些情况先停下：Step 与计划冲突、需要缺失决策、测试反复失败、安全边界不清楚、会跨入后续 Plan、需要破坏性操作、需要外部真实凭据、无关改动影响当前任务。

不要猜着越过安全边界。

---

## 18. 完成定义

一个批次完成必须满足：指定 Step 已实现、相关测试或验证通过、review 问题已处理或分类、必要文档已更新、没有 secret 泄漏、diff 范围干净，并已准备好交给用户手动 commit。

一个 Plan 完成必须满足：所有里程碑验收通过、全量 review 完成、文档和 CHANGELOG 更新、版本 tag 创建、进入下一 Plan 的桥接检查通过。
