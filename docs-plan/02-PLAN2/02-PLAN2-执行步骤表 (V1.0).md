# Plan 2 执行步骤表｜Tool Calling + 简单 Agent Loop

> 适用文档：`00-ALL PLAN/02-PLAN-2 (V1.0).md`  
> 执行方式：每次只领取连续 1～3 个 Step，完成后立即测试、提交、review。  
> 阶段目标：一个阶段完成一个里程碑；一个里程碑通过后再进入下一个里程碑。
> 外部复审策略覆盖（2026-07-18 用户决定）：不再使用 Claude Code；本文件后续所有 Claude Code / Claude review 节点均被此决定覆盖，不作为验收或推进门槛。每批只执行 Codex self-review；全部 6 个 Plan 和整个项目完成后，再由用户决定是否使用 Fable 5 做一次全项目检查。

---

## 0. 执行总原则

| 规则 | 说明 |
|---|---|
| 单次执行范围 | Cursor / Codex 每次只做 1～3 个连续 Step |
| 执行顺序 | 必须按 `P2-Mx-Sy` 顺序推进，除非 Codex 明确调整 |
| 每步完成定义 | 代码可运行、局部测试通过、相关文档或配置同步 |
| 每个阶段完成定义 | 阶段验收项全部通过，Codex review 后进入下一阶段 |
| 外部复审策略 | 不使用 Claude Code；每批以 Codex self-review 和新鲜验证为 gate；整个项目完成后再由用户决定是否使用 Fable 5 |
| 提交节奏 | 每 1～3 个 Step 一次 commit；每个里程碑结束一次 review commit |
| 文档同步 | Tool Schema、权限边界、Agent API、前端展示变化必须同步 docs 或 README |
| 禁止提前做 | RAG、Embedding、复杂状态机、Planner-Executor、Reflection、Memory、MCP、Shell Tool、写文件工具 |

推荐状态值：

```text
pending
doing
implemented
tested
reviewed
fixed
done
blocked
```

---

## 1. Plan 2 总览

| 阶段 | 里程碑 | 对应原 PLAN2 Step | 核心交付 | 预计时间 | 主要工具 | 审核节点 |
|---|---|---|---|---:|---|---|
| Phase 1 | M1 Plan 1 交接与 Tool 地基 | Step 1～5 | v0.1.0 检查、Tool 抽象、Registry、参数校验、安全边界 | 15～25 h | Codex | Codex review |
| Phase 2 | M2 内置只读工具 | Step 6～8 | read_file、list_dir、可选 web_fetch | 10～20 h | Codex | Codex review |
| Phase 3 | M3 LLM Tools 与 Agent Loop | Step 9～10 | Provider tools 参数、Simple Agent Loop、最大步数和失败处理 | 15～25 h | Codex | Codex review |
| Phase 4 | M4 Agent API 与前端展示 | Step 11～12 | Agent API、Tool Call 前端展示 | 10～20 h | Codex + Cursor | Codex review |
| Phase 5 | M5 测试、文档与封版 | Step 13～15 | Tool / Agent 测试、文档、CHANGELOG、v0.2.0 tag | 10～15 h | Codex + Cursor | Codex review |

---

## 2. 执行节奏表

| 执行批次 | 建议领取范围 | 批次目标 | 完成后动作 | 状态 |
|---|---|---|---|---|
| Batch 1 | P2-M1-S1～S3 | 确认 Plan1 地基，建立 Tool 核心结构 | 跑现有测试，提交 Tool 抽象 | 已完成 |
| Batch 2 | P2-M1-S4～S6 | 实现 Registry、参数校验和安全策略雏形 | Tool 单元测试 | 已完成 |
| Batch 3 | P2-M1-S7～S8 | 持久化 AgentRun / ToolCall，完成 M1 review | Codex review M1（Claude Code 未运行） | 已完成 |
| Batch 4 | P2-M2-S1～S3 | 实现 read_file 并覆盖路径安全测试 | 工具测试 | 已完成 |
| Batch 5 | P2-M2-S4～S6 | 实现 list_dir 和工具注册 | 工具集成测试 | 已完成 |
| Batch 6 | P2-M2-S7 | 可选实现 web_fetch 或明确延期记录 | Codex review M2 | 已完成（deferred） |
| Batch 7 | P2-M3-S1～S3 | 扩展 LLM Provider 支持 tools | Provider mock 测试 | 已完成 |
| Batch 8 | P2-M3-S4～S6 | 实现 Simple Agent Loop | Agent mock 测试 | 已完成 |
| Batch 9 | P2-M3-S7～S8 | 完成失败处理、最大步数、工具结果压缩雏形 | Codex review M3 | 已完成 |
| Batch 10 | P2-M4-S1～S3 | 实现 Agent API 和 Tool Call 查询 | API 测试 | 已完成 |
| Batch 11 | P2-M4-S4～S6 | 前端展示 Agent Run 和 Tool Call | 浏览器手测 | 已完成 |
| Batch 12 | P2-M5-S1～S3 | 补 Tool / Agent 测试 | 后端测试 | 已完成 |
| Batch 13 | P2-M5-S4～S6 | 补文档、README、截图和限制说明 | 文档 review | 已完成 |
| Batch 14 | P2-M5-S7～S8 | 最终 review、修复、v0.2.0 封版 | Codex final review | 进行中（S7 done；S8 tag pending） |

---

## 3. Phase 1｜M1 Plan 1 交接与 Tool 地基

阶段目标：

```text
确认 v0.1.0 Chat 底座稳定，并建立 Tool Calling 的核心抽象、注册、校验、安全边界和持久化模型。
```

阶段验收：

```text
1. Plan 1 的 Chat / Streaming / Provider / 会话系统仍可用
2. Tool 抽象和 ToolResult 结构稳定
3. Tool Registry 可以注册和查询工具
4. 工具参数可以按 schema 校验
5. read-only 路径安全策略明确
6. agent_runs / tool_calls 数据模型可用
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P2-M1-S1 | 检查 Plan 1 封版状态和 v0.1.0 tag | Codex | Plan 1 验收记录（见下文） | 后端、前端、Chat、Streaming 均可启动或有明确证据 | Codex（done） |
| P2-M1-S2 | 创建 Tool 模块目录和基础类型 | Codex | `backend/app/tools/base.py`、`Tool`、`ToolResult`、`ToolError` | Tool 类型测试通过 | Codex（done） |
| P2-M1-S3 | 定义 ToolCall 请求 / 响应 schema | Codex | `backend/app/schemas/tool.py` | Pydantic schema 测试通过 | Codex（done） |
| P2-M1-S4 | 实现 Tool Registry | Codex | `backend/app/tools/registry.py` | 注册、查找、重复注册测试通过 | Codex（done） |
| P2-M1-S5 | 实现工具参数校验 | Codex | JSON Schema 或 Pydantic 校验逻辑 | 缺参、类型错误、未知参数测试通过 | Codex（done） |
| P2-M1-S6 | 实现只读路径安全边界 | Codex | `backend/app/tools/security.py` | 禁止读取 `.env`、目录穿越、工作区外路径测试通过 | Codex（done；Claude Code 未运行） |
| P2-M1-S7 | 创建 `agent_runs` 和 `tool_calls` ORM 模型与迁移 | Codex | `backend/app/models/agent_run.py`、`tool_call.py` | 数据库迁移和模型测试通过 | Codex（done） |
| P2-M1-S8 | 完成 M1 review 和文档记录 | Codex | `docs/10-tool-calling-design.md` 初版 | 文档说明 Tool 抽象、Registry、权限边界 | Codex（done；Claude Code 未运行） |

### P2-M1-S1 交接验收记录（2026-07-14）

| 验收项 | 结果与证据 |
|---|---|
| Release commit 与 tag | 执行前工作区干净；`main`、`origin/main`、HEAD 和 annotated tag `v0.1.0` 的 peeled commit 均为 `4802d4348353d86357a89e99b8a32177546ad4f9`；tag 消息为 `AI Agent Lab v0.1.0`。 |
| Plan 1 封版事实 | `README.md`、`README_CN.md`、`CHANGELOG.md`、Foundation、Provider 文档和最终复审记录均确认 Plan 1 范围、Mock 发布证据与已接受限制；发布后的架构阶段、Batch 12 和 tag 状态错漏已在本 Step 修正。 |
| Backend | 新鲜全量验证为 `114 passed, 1 warning`；warning 是已知 Starlette TestClient/httpx 弃用提示；`pip check` 返回 `No broken requirements found.`。 |
| Frontend | `npm run typecheck` 通过；完整 Vitest 为 8 files / 37 tests passed；production build 成功，Vite 转换 1804 个模块。 |
| SQLite 与 API 启动 | 仅使用全新系统临时 SQLite；`alembic upgrade head`、`current --check-heads`、`alembic check` 通过且临时库已删除。Uvicorn health 200、OpenAPI 200、6 个要求路由齐全、服务端 request ID 为 UUID，临时端口和日志已清理。 |
| Chat 与 Streaming | 后端全量测试包含 Mock Provider 的普通 Chat、SSE、事务提交/回滚、取消与安全错误路径；前端全量测试覆盖 SSE reader 释放、迟到响应保护、停止与刷新恢复。最终复审还保留 Mock 浏览器的模型、会话、SSE、URL 刷新恢复和桌面/移动布局证据。未调用真实或付费 Provider。 |
| 文档与安全 | 10 份 release/交接相关文档中的 27 个本地链接全部存在；桌面/移动截图大小与 SHA-256 匹配封版记录；tracked secret 扫描只命中测试假值或变量，未发现真实凭据，且无 tracked `.env`。 |
| Plan 边界 | 本 Step 未创建 `backend/app/tools`、`backend/app/agents` 或任何未来目录，未实现 Tool、Registry、Agent、RAG、Memory 或其他后续能力。 |

**S1 完成时结论：** `P2-M1-S1` 已完成，Plan 1 以 `v0.1.0` 正式封版并满足进入 Plan 2 的桥接条件。当时 Batch 1 仍保持未完成，因为 `P2-M1-S2`～`S3` 尚未开始；下一批从 `P2-M1-S2` 继续。

### P2-M1-S2～S3 Tool 地基验收记录（2026-07-14）

| 验收项 | 结果与证据 |
|---|---|
| Tool 基础契约 | 新增 `Tool` 异步抽象、构造元数据校验、参数 schema 防调用方突变复制、正数超时约束、`ToolResult` 成功/失败一致性校验和 `ToolError` 基础异常。 |
| ToolCall schema | 新增 Provider/数据库中立的 `tool_call_id`、严格的请求参数结构、6 个显式 ToolCall 状态，以及非终态/终态结果一致性和工具名关联校验。 |
| TDD 证据 | S2 RED 因 `app.tools` 缺失而失败，GREEN 为 19 passed；S3 RED 因 ToolCall schema 尚未导出而失败，GREEN 为 24 passed；聚焦合并验证为 43 passed。 |
| 全量验证 | Backend 为 `157 passed, 1 warning`，warning 仍是已知 Starlette TestClient/httpx 弃用提示；`pip check` 无破损依赖。Frontend typecheck、8 files / 37 tests 和 production build 均通过。 |
| 安全与边界 | 测试只使用进程内 Mock Tool，不读取 `.env`、用户数据库或本地文件，不调用真实 Provider、外部 API 或命令。未实现 Registry、JSON Schema 参数校验、路径安全、内置工具、ORM、Agent、API 或前端能力。 |

**结论：** `P2-M1-S2`～`S3` 已完成，Batch 1 的 `P2-M1-S1`～`S3` 全部验收通过。下一批可进入 `P2-M1-S4`～`S6`，但本批未提前实现这些能力。

### P2-M1-S4～S6 Tool Registry、参数校验与安全边界验收记录（2026-07-17）

| 验收项 | 结果与证据 |
|---|---|
| Tool Registry | 新增精确名称注册和查询、注册顺序、重复/未知名称错误、无效 schema 原子拒绝及 OpenAI function schema 防御性复制；Registry 聚焦测试为 8 passed。 |
| 参数校验 | 使用 `jsonschema 4.26.0` 和 JSON Schema Draft 2020-12；缺参、类型错误、未知参数、嵌套路径、多错误稳定排序和不回显参数值均由测试覆盖；参数校验聚焦测试为 8 passed。 |
| 安全边界 | 仅用 `tmp_path` 验证相对路径、绝对/盘符/UNC、`..`、Windows 尾随点/空格别名和备用数据流、工作区外路径、`.env`、敏感目录、私钥、文件大小和目录深度策略；安全聚焦测试为 33 passed，未读取任何目标文件。 |
| 聚焦与全量验证 | S2～S6 Tool 聚焦套件为 92 passed。完整 Backend 为 `206 passed, 1 warning`，warning 仍是已知 Starlette TestClient/httpx 弃用提示；`pip check` 无破损依赖。Frontend typecheck、8 files / 37 tests 和 production build（1804 modules transformed）均通过。 |
| 安全与边界 | 未读取真实 `.env`、用户数据库或凭据，未调用 Provider；未实现 builtin Tool、ORM、迁移、Agent、API、前端、RAG、Memory 或 MCP。S6 由 Codex 完成 review，未运行可选 Claude Code 复审。 |

**结论：** `P2-M1-S4`～`S6` 和 Batch 2 已完成。M1 尚未完成，下一批可进入 `P2-M1-S7`～`S8`，但本批未实现持久化、M1 总复审或任何后续能力。

S4～S6 完成时建议 commit：

```text
feat(tools): add tool abstractions registry and safety boundary
```

### P2-M1-S7～S8 Agent 持久化与 M1 总复审记录（2026-07-17）

| 验收项 | 结果与证据 |
|---|---|
| AgentRun / ToolCall 模型 | 新增 UUID 数据库身份、独立 `tool_call_id` 关联身份、Conversation/Message 关联、JSON 参数与结果、状态/耗时约束及索引。AgentRun 与 ToolCall 的复合外键禁止跨 Conversation 归属，单次 run 内关联 ID 唯一。模型聚焦测试为 `9 passed`。 |
| 迁移 | 新增线性 revision `20260717_0002`；迁移测试覆盖表、列、外键删除动作、索引、唯一/检查约束及降级保留 Plan 1 表，迁移套件为 `4 passed`。全新系统临时 SQLite 上 `upgrade head`、`current --check-heads`、`alembic check`、降级到 `20260712_0001` 和再次升级均通过，临时库已删除。 |
| TDD 与回归修复 | ORM RED 因模型尚未导出而失败，GREEN 为 `9 passed`；迁移 RED 因新 revision/表尚不存在而失败。全量测试首次暴露进程内 Alembic 日志配置污染 `caplog`，失败顺序稳定复现后仅将迁移测试改为无日志副作用的编程式配置；同序回归为 `3 passed`。 |
| 全量验证 | Backend 为 `217 passed, 1 warning`，warning 仍是已知 Starlette TestClient/httpx 弃用提示；`pip check` 无破损依赖。Frontend typecheck、8 files / 37 tests 和 production build（1804 modules transformed）均通过。 |
| 文档与安全 | 新增 `docs/10-tool-calling-design.md`，并同步 README、项目概览和架构阶段。检查 22 个本地 Markdown 链接均存在；变更文件秘密模式扫描、生成物检查、`CHANGELOG.md` 未改检查及 `git diff --check` 均通过。 |
| Codex M1 review | ORM/迁移结构与删除语义一致，`alembic check` 无元数据漂移；UUID 与 Provider 关联 ID 分离；状态、负耗时、重复关联 ID、跨 Conversation 归属及删除行为均有测试。未发现阻塞项。未运行 Claude Code，因为用户未明确要求外部复审。 |
| 安全与 Plan 边界 | 未读取真实 `.env`、用户数据库或凭据，未调用真实 Provider。未创建 `backend/app/agents` 或 builtin Tool 目录，未实现内置工具、Provider tools、Agent Loop、Agent service/API、前端 Agent 视图、RAG、Memory 或 MCP。 |

**结论：** `P2-M1-S7`～`S8`、Batch 3 和 Plan 2 M1 已完成。下一批可进入 `P2-M2-S1`～`S3`，但本批未提前实现 read_file 或任何后续能力。

S7～S8 建议 commit：

```text
feat(agent): add agent run and tool call persistence
```

---

## 4. Phase 2｜M2 内置只读工具

阶段目标：

```text
实现 Plan 2 的最小只读工具集，让 Agent 能安全读取项目文件和查看目录。
```

阶段验收：

```text
1. read_file 可读取允许范围内的文本文件
2. list_dir 可列出允许范围内的目录
3. 工具失败时返回 ToolResult error，不让系统崩溃
4. read_file / list_dir 自动注册到 Tool Registry
5. web_fetch 如执行则只能作为低风险文本抓取工具；如延期则在文档中记录
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P2-M2-S1 | 实现 read_file 工具 | Codex | `backend/app/tools/builtin/read_file.py` | 可读取 README，返回文本内容和 metadata | Codex（done） |
| P2-M2-S2 | 为 read_file 添加安全和异常测试 | Codex | read_file 测试 | `.env`、二进制文件、超大文件、目录穿越均被拒绝或安全处理 | Codex（done） |
| P2-M2-S3 | 将 read_file 注册到 Tool Registry | Codex | builtin tool 初始化逻辑 | Registry 能列出 read_file | Codex（done） |
| P2-M2-S4 | 实现 list_dir 工具 | Codex | `backend/app/tools/builtin/list_dir.py` | 可列出项目内目录，返回文件名、类型、大小 | Codex（done） |
| P2-M2-S5 | 为 list_dir 添加安全和异常测试 | Codex | list_dir 测试 | 工作区外路径、隐藏敏感文件、无权限路径安全处理 | Codex（done） |
| P2-M2-S6 | 将 list_dir 注册到 Tool Registry 并补工具列表测试 | Codex | builtin tools registry 测试 | Registry 能列出 read_file / list_dir | Codex（done） |
| P2-M2-S7 | 评估并处理 web_fetch：实现低风险版本或记录延期 | Codex | docs 延期与限制说明 | README / docs 明确未实现、延期原因和重评边界 | Codex review（done：deferred） |

### P2-M2-S1～S3 read_file 验收记录（2026-07-18）

| 验收项 | 结果与证据 |
|---|---|
| read_file 契约 | 新增异步 `ReadFileTool`，参数仅允许必填字符串 `path`；默认工作区根目录、1 MiB 文件上限和 100,000 返回字符上限均可注入。成功结果包含 UTF-8 文本、规范化相对路径、字节/字符计数和截断状态；默认配置安全读取 tracked `README.md`。 |
| 安全与异常 | 复用 M1 路径边界；参数错误、`.env`、私钥、目录穿越、缺失文件、目录、超大文件、NUL、非 UTF-8 和 `OSError` 均返回固定安全失败 ToolResult，不回显参数值、绝对路径、文件内容或原始异常。文件读取通过 `asyncio.to_thread`，单次最多请求 `max_file_bytes + 1` 字节。 |
| Registry | 新增 caller-controlled `register_builtin_tools()`，可将配置后的 read_file 注册到现有 Registry 并导出 OpenAI-compatible schema；重复调用保持显式 DuplicateTool 错误，无 singleton、import-time 或应用启动副作用。 |
| TDD 证据 | S1 RED 因 `app.tools.builtin` 缺失而 collection 失败，GREEN 为 11 passed；S2 新增 12 个失败路径后为 12 failed / 11 passed，GREEN 为 23 passed；S3 RED 因 `register_builtin_tools` 未导出而失败，GREEN 为 26 passed。Codex review 的 bounded-I/O 回归先证明旧实现调用 `read(-1)`，修复后 read_file 聚焦为 `27 passed`，完整 Tool foundation 为 `119 passed`。 |
| 全量验证 | Backend 为 `244 passed, 1 warning`，warning 仍是已知 Starlette TestClient/httpx 弃用提示；`pip check` 无破损依赖。Frontend typecheck、8 files / 37 tests 和 production build（1804 modules transformed）均通过；首次 build 的 `dist` 写入 EPERM 已确认是受管沙箱权限限制，使用已批准 build 权限重跑成功。 |
| 文档与检查 | README、中英文当前阶段、项目概览、架构和 Tool Calling 设计已同步；22 个本地 Markdown 链接存在，变更文件秘密模式、生成物、Step 边界、`CHANGELOG.md` 未改及 diff 检查均通过。 |
| Codex review 与边界 | 必须修 1 项（文件增长竞态下无界 `read_bytes()`）已按 RED/GREEN 改为限长读取；计划遗漏的项目概览同步已补齐。无剩余阻塞项。未运行 Claude Code，因为本执行行仅要求 Codex 且用户未明确要求外部复审。未实现 `list_dir`、`web_fetch`、Provider tools、Agent Loop、service/API、前端 Agent 视图、RAG、Memory、MCP、Shell 或写文件能力。 |

**结论：** `P2-M2-S1`～`S3` 和 Batch 4 已完成；后续 `S4`～`S6` 的实现与验收记录见下节。

S1～S3 建议 commit：

```text
feat(tools): add safe read file builtin
```

### P2-M2-S4～S6 list_dir 验收记录（2026-07-18）

| 验收项 | 结果与证据 |
|---|---|
| list_dir 契约 | 新增异步只读 `ListDirTool`，接受必填 `path` 和可选 `max_depth`；默认深度 2、硬上限 3、默认最多 500 条。成功结果同时返回逐行 `content`、结构化 `data.entries` 以及根路径、深度、条目数和截断状态 metadata。 |
| 遍历与安全 | 工作区相对路径复用 M1 sandbox；条目按规范化相对路径稳定排序，文件返回字节大小，目录返回空大小。`.git`、`.env*`、`.ssh`、`docs-local`、`__pycache__` 和私钥类名称在 metadata 读取和递归前过滤；普通 `.gitignore` 可见；符号链接只报告、不跟随；所有目录 metadata 工作进入 `asyncio.to_thread`。 |
| 异常处理 | 参数错误、越界/敏感根路径、缺失路径、非目录和权限/文件系统异常均返回固定失败 ToolResult，不回显参数、绝对路径、目录内容或原始异常。测试只使用临时工作区，未读取真实 secret、Provider 配置或用户数据库。 |
| Registry | `register_builtin_tools()` 由调用方持有并按 `read_file`、`list_dir` 顺序注册，支持注入两类 Tool 的限制并导出 OpenAI-compatible schemas；配置或重复名称失败时 Registry 保持不变，无 singleton、import-time 或应用启动副作用。 |
| TDD 证据 | S4 RED 因 `app.tools.builtin.list_dir` 不存在而 collection 失败，GREEN 为 `11 passed`；S5 RED 为敏感项过滤 `1 failed, 24 passed`，GREEN 与共享 security 测试为 `58 passed`；S6 RED 为双工具注册 `2 failed, 25 passed`，GREEN 为双 builtin 聚焦 `52 passed`、Tool foundation `144 passed`。Codex review 的原子性回归先为 `2 failed`，修复后为 `2 passed`，最终双 builtin 聚焦 `54 passed`、Tool foundation `146 passed`。 |
| 全量验证 | Backend 为 `271 passed, 1 warning`，warning 仍是已知 Starlette TestClient/httpx 弃用提示；`pip check` 无破损依赖。Frontend typecheck、8 files / 37 tests 和 production build（1804 modules transformed）均通过；build 使用已批准权限规避受管沙箱对 `dist` 的已知写限制。 |
| 文档与检查 | 中英文 README、项目概览、架构和 Tool Calling 设计已同步；31 个本地 Markdown 链接存在，变更文件秘密模式 0、Git 可见 Python 生成物 0、越界能力代码命中 0，`CHANGELOG.md` 未改，diff 检查通过。pytest 生成的 70 个本地 `.pyc` 均被忽略且未进入 Git。 |
| Codex review 与边界 | 必须修 1 项：双工具初始化在无效 `list_dir` 配置或预存同名 Tool 时会留下部分注册；已按 RED/GREEN 改为构造和重复检查全部成功后再写 Registry，并完成聚焦、Tool foundation 与后端全量复验。无剩余阻塞项。未运行 Claude Code，因为用户未明确要求外部复审。未实现 S7、Provider tools、Agent Loop、service/API/frontend Agent 视图、RAG、Memory、MCP、Shell 或写文件能力。 |

**结论：** `P2-M2-S4`～`S6` 已完成；后续 S7 的评估与延期决策见下节，本批没有提前实现 `web_fetch`。

S4～S6 建议 commit：

```text
feat(tools): add safe list directory builtin
```

### P2-M2-S7 web_fetch 评估与 M2 review 记录（2026-07-18）

| 验收项 | 结果与证据 |
|---|---|
| 决策 | 采用计划允许的延期路径：Plan 2 不实现 `web_fetch`。M2 以 `read_file` 与 `list_dir` 两个只读内置 Tool 收口。 |
| 延期原因 | 可信网络 Tool 必须完整处理 scheme/port、SSRF、DNS 与重绑定、每次重定向复验、严格超时、有界流式响应、内容类型/解码、HTML 正文提取和安全错误；只实现其中一部分会形成误导性的“低风险”能力。 |
| 可执行边界 | 未创建 `web_fetch.py`、`WebFetchTool`、URL/network helper、依赖、配置、测试、Registry schema、API 或前端 UI；未发起真实网络请求或 Provider 调用。 |
| 重评边界 | 候选重评点为 Plan 4 或 Plan 6，但不承诺采用当前 Tool 形态；未来必须先批准完整网络权限、重定向/地址验证、提取和 Mock 验收契约。 |
| 全量验证 | Backend `271 passed, 1 warning`，`pip check` 通过；Frontend typecheck、8 files / 37 tests 和 production build（1804 modules transformed）通过。warning 仍是已知 Starlette TestClient/httpx 弃用提示。 |
| 文档与检查 | README/README_CN、项目概览、架构、Tool Calling 设计和执行表事实一致；最终复验记录 31 个本地 Markdown 链接、秘密模式 0、Git 可见生成物 0、无网络 Tool surface、`CHANGELOG.md` 未改和 diff 检查通过。 |
| Codex M2 review | 必须修 1 项：验收记录曾预填 32 个本地 Markdown 链接，实际完整扫描为 31 个；已按真实证据纠正并复验。纯文档 diff 与批准方案一致，无剩余阻塞项。确认未进入 Provider tools、Agent Loop、service/API/frontend Agent 视图或后续 Plan。未运行 Claude Code，因为用户未明确要求外部复审。 |

**结论：** `P2-M2-S1`～`S7` 与 M2 已完成。下一批进入 `P2-M3-S1`～`S3`，本 Step 没有实现或暴露 `web_fetch`。

S7 建议 commit：

```text
docs(plan2): defer web fetch tool
```

M2 完成后建议 commit：

```text
feat(tools): add read only builtin tools
```

---

## 5. Phase 3｜M3 LLM Tools 与 Agent Loop

阶段目标：

```text
把 Tool Registry 接入 LLM Provider，建立 Simple Agent Loop，让模型可以选择工具、执行工具、再生成最终答案。
```

阶段验收：

```text
1. LLM Provider 支持 tools 参数
2. OpenAI-compatible Provider 能发送 tool definitions
3. Agent Loop 能执行最多 N 步
4. 工具调用结果能进入下一轮模型上下文
5. AgentRun / ToolCall 会记录状态、耗时、错误和结果摘要
6. 工具失败不会导致整个 API 崩溃
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P2-M3-S1 | 扩展 LLMProvider `chat` 接口支持 tools | Codex | Provider base interface 更新 | mock provider 可接收 tools 参数 | Codex（done） |
| P2-M3-S2 | 扩展 OpenAI-compatible Provider 的 tool calling 请求和响应解析 | Codex | provider tool call 支持 | mock response 能解析 tool call | Codex（done） |
| P2-M3-S3 | 实现 Tool Schema 转换为模型可用格式 | Codex | tool schema adapter | read_file / list_dir schema 可序列化 | Codex（done） |
| P2-M3-S4 | 创建 Simple Agent Loop 基础流程 | Codex | `backend/app/agents/simple_agent.py` | 无工具任务直接返回答案 | Codex（done） |
| P2-M3-S5 | 接入工具选择、执行和 observation 回填 | Codex | Agent 调用 Tool Registry | 固定 mock 模型触发 read_file 后生成最终答案 | Codex（done） |
| P2-M3-S6 | 持久化 AgentRun 和 ToolCall | Codex | Agent run service | 每次工具调用都有数据库记录 | Codex（done） |
| P2-M3-S7 | 实现最大步数、超时、失败返回 | Codex | runtime policy 常量或配置 | 超过最大步数返回可读错误 | Codex（done） |
| P2-M3-S8 | 完成 M3 review 和 Agent Loop 文档 | Codex | `docs/11-simple-agent-loop.md` | 文档解释 Agent Loop 流程和限制 | Codex review（done） |

### P2-M3-S1～S3 Provider tools 验收记录（2026-07-18）

| 验收项 | 结果与证据 |
|---|---|
| Provider 契约 | `ChatRequest` 新增有序强类型 `tools`，空值保持普通 Chat payload 不变；`LLMResponse` 支持文本、一个或多个规范化 `LLMToolCall`，并拒绝无输出或重复 Tool Call ID。Tool 名称、ID、object 根参数 schema 和 JSON 序列化在本地校验。 |
| Registry adapter | 新增 `build_llm_tool_definitions()`，按 caller-owned Registry 顺序将 `read_file`、`list_dir` 转为顶层 frozen 的 Provider 定义；不执行 Tool、不访问工作区、不依赖 builtin 类型，schema 输入与序列化结果具备防御性复制。 |
| OpenAI-compatible | 非流式请求仅在 tools 非空时发送标准 `tools` 数组；响应按原顺序解析 `message.tool_calls`，把 arguments JSON 字符串规范化为 object。非法 shape、非标准 JSON 常量、非 object、无效名称/ID、重复 ID 或未请求的 Tool Call 均返回固定安全 `ProviderResponseError`，不回显原始 arguments。 |
| Streaming 与 Plan 1 兼容 | 带 tools 的流式请求在 HTTP 前以固定 `ProviderUnsupportedFeatureError` 失败；现有文本 Chat 不发送 Tool 定义，若意外收到纯 Tool Call 响应则固定报错并完整回滚。Provider/Chat/API 联合回归为 `68 passed, 1 warning`。 |
| TDD 证据 | Contract RED 因新 DTO 缺失而 collection 失败，GREEN 为 `17 passed`；adapter RED 因模块缺失而失败，GREEN 为 `4 passed`；OpenAI happy-path RED 为 `2 failed, 17 passed`，GREEN 为 `19 passed`；非标准 `NaN` 回归先为 `1 failed, 28 passed`，修复后 Provider 文件为 `29 passed`；Tool-only Chat 回归先暴露 Pydantic `ValidationError`，修复后通过。Codex self-review 又补齐 6 个缺失字段及空/超长 ID 用例，并增加完整 Registry schema 等值断言，最终 Provider+adapter 聚焦为 `40 passed`。 |
| 完整验证 | Provider/Tool/Chat 聚焦为 `162 passed, 1 warning`；Backend 为 `344 passed, 1 warning`，`pip check` 无破损依赖。Frontend typecheck、8 files / 37 tests 和 production build（1804 modules transformed）通过；首次 build 的 `dist` EPERM 为受管沙箱限制，按已批准权限重跑成功。FastAPI 临时内存 SQLite smoke 为 health 200、OpenAPI 200、服务端 request ID UUID，未初始化真实 Provider。 |
| 文档、能力与边界 | README 中英文、项目概览、架构、Provider 文档和 Tool Calling 设计已同步；31 个 committed-scope 本地 Markdown 链接存在，秘密模式、tracked 生成物、迁移变更、`web_fetch` runtime surface 和 API/前端/后续 Plan 变更均为 0，diff/新文件空白检查通过。tracked 示例模型继续为 `supports_tools=false`；未执行 Tool，未实现 Agent Loop、observation、AgentRun/ToolCall service、Agent API、前端或后续 Plan；未调用真实 Provider、网络 Tool 或付费服务。仅执行 Codex self-review，不使用 Claude Code。 |

**结论：** `P2-M3-S1`～`S3` 与 Batch 7 已完成。下一批为 `P2-M3-S4`～`S6`；本批只建立 Provider transport，不代表 M3 或 Agent Loop 已完成。

S1～S3 建议 commit：

```text
feat(provider): add non-streaming tool calling support
```

S4～S6 建议 commit：

```text
feat(agent): add simple tool calling loop
```

### P2-M3-S4～S6 Simple Agent Loop 验收记录（2026-07-19）

| 验收项 | 结果与证据 |
|---|---|
| Provider observation 契约 | `ChatMessage` 可强类型表达普通文本、assistant Tool Calls 与带 correlation ID 的 Tool observation；非法 role/字段组合和重复 ID 本地拒绝。OpenAI-compatible adapter 独占 assistant `tool_calls` 与 `role=tool` wire 映射，普通 Plan 1 payload 保持不变。手工构造的 `LLMToolCall.arguments` 也必须是标准 JSON object。 |
| S4 直接回答 | 新增 `app.agents.SimpleAgentService`、frozen 请求 DTO、不可变结果和固定 Agent domain errors。服务在任何写入前校验模型存在、`supports_tools=true` 和 Provider 可用；无 Tool 响应只调用 Provider 一次，保存 Conversation、用户/助手 Message 和 completed AgentRun，不创建 ToolCall。 |
| S5 Tool 闭环 | 首轮可返回一个或多个 Tool Call，服务按 Provider 顺序执行 Registry lookup、统一参数校验和 Tool；随后回填一条 assistant Tool Call 消息及逐调用 observations，并只再调用 Provider 一次取得最终文本。未知 Tool、参数失败、ToolResult 失败、异常、名称不匹配和非标准 JSON ToolResult 均变成安全失败 observation；第二次仍请求 Tool 时固定失败且不进行第三次调用。 |
| S6 持久化 | 每次尝试的 Tool Call 在 lookup/validation 前创建 ORM 行，结束后保存 arguments、完整 ToolResult、success/failed 状态、安全 error、开始/结束时间和 latency。成功运行的 AgentRun 保存 goal、用户消息关联、final answer 和计时；commit/expire/reload 证明 SQLite round-trip。未新增 migration 或状态。 |
| TDD 证据 | Provider message RED 为 `5 failed, 22 passed`，GREEN 为 `27 passed`；wire RED 为 `1 failed, 36 passed`，Provider/Chat GREEN 为 `75 passed, 1 warning`。Agent module RED 为 collection error，Gate GREEN 为 `9 passed`；S4 RED 为 `3 failed, 9 passed`，GREEN 联合回归为 `50 passed, 1 warning`；read_file RED 为 `1 failed, 12 passed`，GREEN 为 `13 passed`；安全边界 RED 为 `4 failed, 16 passed`，Agent/Tool GREEN 为 `97 passed`；S6 RED 为 `1 failed, 20 passed`，GREEN 为 `21 passed`。Codex 自审补充非标准 JSON ToolResult 回归，先 `1 failed, 3 passed`，修复后 `4 passed`，Agent/Tool 为 `100 passed`。 |
| 完整验证 | 功能聚焦 `220 passed, 1 warning`；Backend `378 passed, 1 warning`，`pip check` 无破损依赖。Frontend typecheck、8 files / 37 tests 和 production build（1804 modules transformed）通过；首次 build 的 `dist/assets` EPERM 为受管沙箱限制，按已批准 `npm run build` 权限重跑成功。FastAPI smoke 为 health 200、OpenAPI 200、服务端 request ID UUID，未初始化真实 Provider。61 个 committed-scope Markdown 文件中的 31 个本地链接全部存在，疑似真实秘密命中为 0。 |
| 当时限制与边界（S4～S6 历史记录） | 本批没有 Agent API/UI、streaming Tool Calls、通用 max_steps、Tool timeout、retry/cancel 或完整失败返回；这些分别属于 S7～S8 或后续 Milestone。Agent Provider 调用尚未关联 LLMCall，数据库没有显式 ToolCall sequence 字段，失败运行的最终事务策略仍由 S7/API 调用方定义。tracked 示例模型保持 `supports_tools=false`；测试注入 tools-capable Mock Registry。无真实 Provider、网络 Tool、用户数据库、migration、`web_fetch` runtime 或后续 Plan 代码。仅执行 Codex self-review，不使用 Claude Code；Fable 5 只在六个 Plan 全部完成后由用户决定。 |

**结论：** `P2-M3-S4`～`S6` 与 Batch 8 已完成。下一批为 `P2-M3-S7`～`S8`；当前 Simple Agent 是有意限制为一次 Tool round 的后端 service，不代表 M3 review 或 Agent API 已完成。

### P2-M3-S7～S8 有界循环、失败策略与 M3 review 验收记录（2026-07-19）

| 验收项 | 结果与证据 |
|---|---|
| 最大步数 | `SimpleAgentRequest.max_steps` 是严格整数，默认 3、范围 `1..10`；一次 Provider 决策计一步，同一响应多个 Tool Call 只计一步。默认允许两轮 Tool 决策后在第三步返回文本；最后允许步骤仍请求 Tool 时不执行、不建 ToolCall 行、不额外调用 Provider，并返回 failed AgentRun。 |
| Tool timeout | Agent 只在 lookup/参数校验成功后按 Tool 的有限正数 `timeout_seconds` 包裹 `tool.run()`；超时记录 `ToolCall.status=timeout` 和固定 `Tool execution timed out` observation，同轮后续调用与下一次 Provider 决策继续。异步取消是协作式的，没有自动 retry。 |
| 结构化失败 | AgentRun 创建后的最大步数、Provider timeout、其他 Provider/无效返回和空白终态均返回 `assistant_message=None` 的 `SimpleAgentResult`，保存固定安全 error、结束时间和 latency，调用方可以 commit/reload。前置配置错误仍在持久化前抛出；数据库错误与任务取消继续传播供调用方回滚。 |
| Observation 上限 | Provider observation 默认最多 32,000 字符、构造下限 1,024；超限副本按 JSON 转义后的实际长度压缩 content/error，丢弃 data 并记录 truncation metadata。数据库仍保存完整 ToolResult，且测试证明原对象未突变。 |
| TDD 证据 | Request policy RED 为 `1 failed, 10 passed`；多步 RED 为 `1 failed, 1 passed`，终态失败 RED 为 `3 failed`；Provider failure RED 为 `4 failed`；Tool timeout RED 为 `1 failed`；observation RED 为 `3 failed, 5 passed`。每项最小实现后聚焦回归依次达到 `27`、`93`、`120` 和 Agent/Tool `220 passed`。 |
| Codex M3 self-review | 发现 4 个必须修项：跨轮重复 Tool Call ID 撞唯一约束、转义字符使压缩 envelope 超限、`NaN/Infinity` Tool timeout 绕过期限、Provider 返回错误类型逃逸边界。分别先得到 `2 failed`、`3 failed` 和 `1 failed, 1 passed` 的回归红灯，再修复为绿色；最终 M3/Tool 聚焦为 `196 passed, 1 warning`。无剩余阻塞项。 |
| 完整验证 | Backend `402 passed, 1 warning`；warning 是已知 Starlette TestClient/httpx 弃用提示。`pip check` 无破损依赖。Frontend typecheck、8 files / 37 tests、production build（1804 modules transformed）通过。全新系统临时 SQLite 上 Alembic `upgrade head`、`current --check-heads`、`check` 通过且临时库已删除。FastAPI smoke 为 health 200、OpenAPI 200、服务端 request ID UUID，未初始化真实 Provider。 |
| 文档、安全与边界 | 新增 `docs/11-simple-agent-loop.md` 并同步 README 中英文、CHANGELOG、overview、architecture、Provider 和 Tool Calling 文档。64 个 Markdown 文件中的 34 个本地链接/图片均存在；187 个 tracked/本批文本路径的真实 secret 模式命中为 0。没有 migration、Agent API、frontend source、tracked model、`web_fetch` runtime、RAG、Memory、MCP、Shell/write/delete Tool 或真实 Provider/用户数据库操作。 |
| 已接受限制 | Agent service 只 flush、不 commit；M4 API 负责成功/失败结果提交与映射。无自动 retry/cancel/resume、流式 Tool Calls、并行 Tool、单步总 Tool Call 数上限、Agent-linked LLMCall 或显式数据库 sequence。tracked 示例模型继续为 `supports_tools=false`。 |

**结论：** `P2-M3-S7`～`S8`、Batch 9 和 Plan 2 M3 已完成，Codex self-review 与完整验证无阻塞问题。下一批可以进入 `P2-M4-S1`～`S3`，但本批没有实现 Agent API、前端或任何 M4/后续 Plan 能力。没有使用 Claude Code；Fable 5 仍只在全部六个 Plan 完成后由用户决定。

S7～S8 建议 commit：

```text
feat(agent): add bounded agent loop runtime policy
```

---

## 6. Phase 4｜M4 Agent API 与前端展示

阶段目标：

```text
让用户可以通过 API 和前端触发 Agent，并看到工具调用过程、工具结果和最终回答。
```

阶段验收：

```text
1. Agent API 可启动一个简单任务
2. API 返回 final answer、tool calls、status、error
3. 前端可以展示 Tool Call 卡片
4. 用户能看到工具名、参数、状态、耗时、结果摘要
5. 读取 README 并总结项目结构的验收场景可跑通
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P2-M4-S1 | 实现 Agent API 请求 / 响应 schema | Codex | `backend/app/schemas/agent.py` | schema 测试通过 | Codex（done） |
| P2-M4-S2 | 实现 `POST /api/v1/agents/runs` | Codex | `backend/app/api/v1/agents.py` | API 测试可启动 Agent Run | Codex（done） |
| P2-M4-S3 | 实现 Agent Run 查询和 Tool Call 查询接口 | Codex | `GET /agents/runs/{id}`、`GET /agents/runs/{id}/tool-calls` | API 测试通过 | Codex（done） |
| P2-M4-S4 | 创建前端 agent API 封装和类型 | Cursor | `frontend/src/api/agent.ts`、`types/agent.ts` | TypeScript 检查通过 | Codex（done） |
| P2-M4-S5 | 实现 Tool Call 展示组件 | Cursor | `ToolCallCard.tsx`、`ToolCallTimeline.tsx` | 组件可展示 pending / success / error | Codex（done） |
| P2-M4-S6 | 在 Chat 页面或 Agent 页面接入 Agent Run 展示 | Cursor + Codex | Agent 任务输入、结果展示、工具调用过程 | 浏览器手测 README 总结场景 | Codex（done） |

### P2-M4-S1～S3 Agent API 验收记录（2026-07-19）

| 验收项 | 结果与证据 |
|---|---|
| API schema | 新增 `AgentRunCreate`、`AgentRunRead`、`AgentRunExecutionRead` 和 `ToolCallRead`。请求只接受 `input`，拒绝未知字段，`max_steps` 为严格整数 `1..10`、默认 3；API 使用 `arguments`、`result`、`error` 语义字段，不暴露 ORM JSON/message 字段名。 |
| 路由与事务 | 只实现复数 `POST /api/v1/agents/runs`、`GET /api/v1/agents/runs/{run_id}` 和 `GET .../tool-calls`，不提供单数 alias。completed 与结构化 failed AgentRun 都走正常提交路径并返回 HTTP 201；preflight/数据库异常走 rollback，commit failure 测试证明不会返回伪 201。 |
| 查询边界 | 未知 AgentRun 返回安全 `agent_run_not_found` 404，已存在但无 ToolCall 返回 `[]`；ToolCall 查询按 `created_at, id` 确定性排序但不宣称严格 sequence。两个 GET 只依赖 Session，测试用抛出私有诊断的 Provider dependency 证明查询不会解析 Provider 配置。 |
| Tool 与错误安全 | POST 每请求构造只含 `read_file`/`list_dir` 的 Registry。临时目录 `read_file` Tool round 返回并持久化完整 ToolCall，不泄漏绝对路径；模型不存在、不支持 Tools、Provider 不可用、Conversation/AgentRun 不存在、请求和数据库错误均返回固定脱敏 envelope。 |
| TDD 证据 | Schema RED 因 `app.schemas.agent` 不存在而 collection error，GREEN 为 10 passed；Service RED 因 `AgentRunNotFoundError` 不存在而 collection error，GREEN 为 6 passed；路由 RED 为 OpenAPI 缺失与 POST 404（2 failed），GREEN 为 2 passed。Tool、失败、查询和事务集成完成后 Agent API/service 为 41 passed。 |
| Codex self-review | 发现 1 个必须修项：把 `AgentService` 加入 `app.services.__init__` 会形成 `agents.errors -> services package -> agent_service -> agents` 循环导入，首次 GREEN 以可重复 ImportError 暴露；移除该包级导出、改用明确模块入口后 service 6 passed、schema 10 passed，聚焦回归两次均为 322 passed, 1 warning。无剩余阻塞项。 |
| 完整验证 | Backend `443 passed, 1 warning`，warning 是已知 Starlette TestClient/httpx 弃用提示；`pip check` 无破损依赖。Frontend typecheck、8 files / 37 tests、production build（1804 modules transformed）通过。全新系统临时 SQLite 上 Alembic `upgrade head`、`current --check-heads`、`check` 通过，head 为 `20260718_0003` 且临时库已删除。FastAPI mock smoke 10 passed，覆盖 health、OpenAPI、服务端 request ID、Agent POST/GET 和无 Provider 查询。 |
| 文档、安全与边界 | 新增 `docs/12-agent-api.md` 并同步 README 中英文、CHANGELOG、overview、architecture、Simple Agent 和执行表。67 个 Markdown 文件中的 43 个本地链接/图片均存在；189 个 tracked/本批文本路径的真实 secret 模式命中为 0。21 个变更路径均属于 S1～S3/文档，禁止目录、生成物/敏感产物、staged 文件、单数 runtime 路由和后续 Plan runtime 命中均为 0。 |
| 已接受限制 | tracked 示例模型继续为 `supports_tools=false`；没有真实 Provider 验收。前端 Agent API/ToolCall 视图属于 S4～S6；流式 Tool Calls、自动 retry/cancel/resume、Agent-linked LLMCall 与严格持久化 sequence 仍未实现。 |

**结论：** `P2-M4-S1`～`S3` 与 Batch 10 已完成，Codex self-review 和完整验证无阻塞问题。M4 尚未完成；下一批只能进入 `P2-M4-S4`～`S6`。没有使用 Claude Code、Fable 5 或子代理，也没有实现 M5、Plan 3 或后续能力。

S1～S3 建议 commit：

```text
feat(agent): add agent run api
```

### P2-M4-S4～S6 Agent/ToolCall 前端验收记录（2026-07-19）

| 验收项 | 结果与证据 |
|---|---|
| 前端契约与导航 | 新增与公开 Agent API 一致的 TypeScript 类型、只调用复数 `/agents/runs` 的 API wrapper、安全 `AgentApiError`，以及保留其他查询参数的 Chat/Agent/run URL helper。`App` 使用轻量 URL 状态切换工作台，不引入 Router 或新状态库；Chat 页面只增加导航入口。 |
| Agent 工作台 | 独立 Agent 页面只列出 `supports_tools=true` 的 Registry 模型，覆盖 workspace/model loading、empty、no-model、completed、结构化 failed 201、transport error 与 URL restore。同步提交完成后显示 final answer/status/error、AgentRun/Conversation ID，并并行读取已持久化 AgentRun 与 ToolCalls。 |
| ToolCall 展示 | `ToolCallCard`/`ToolCallTimeline` 按 API 顺序展示 pending/running/success/failed/timeout/blocked，保留 Tool 名、参数、状态、耗时、结果摘要、安全错误、Provider call ID 和数据库 ID；JSON 确定性排序，结果摘要默认限制 600 字符，React 文本转义测试覆盖脚本字符串。 |
| TDD 与自审修复 | API、URL、格式化、组件、表单、页面和真实 App 导航均先验证 RED 再实现 GREEN。Codex self-review 额外发现离开 Agent 页面后迟到响应可能改写 Chat URL；回归测试先得到 `1 failed, 4 passed`，加入 request gate 后聚焦验证为 `2 files / 7 tests`，最终前端为 `16 files / 79 tests`。 |
| Mock 浏览器验收 | 未调用真实 Provider。桌面 1280px 与移动 390×844 均无横向溢出；README 总结场景显示 final answer、`read_file`、`README.md` 参数、success、25ms 和全部追踪 ID，URL 写入 run UUID。另验收默认 Chat、Tools 模型过滤、loading、no-model、结构化 failed 201、安全 HTTP 503 + Request ID、GET restore；临时截图/浏览器目录和本批 Vite 进程均已清理，未提前创建 M5 release asset。 |
| 完整验证 | Backend `443 passed, 1 warning`，warning 是已知 Starlette TestClient/httpx 弃用提示；`pip check` 无破损依赖。Frontend typecheck、`16 files / 79 tests`、production build（1812 modules transformed）通过。所有 Provider/API 浏览器响应均为本地 Mock。 |
| 文档、安全与边界 | README 中英文、CHANGELOG、overview、architecture、Agent API 和执行表同步至 M4 S6。69 个 Markdown 文件中的 45 个本地链接/图片均存在；31 个本批变更路径的真实 secret 模式命中为 0。没有 backend/model/migration/provider/tool 改动，没有 tracked 生成物、数据库或 `.env`，也没有单数 Agent 路由、真实 Provider host、`web_fetch` 或后续 Plan runtime 表面。 |
| Codex self-review | 必须修：迟到响应边界已按 TDD 修复。后续 Step：正式 release 截图仍按 M5-S6 生成。记录限制：同步非流式、无 run list/polling/cancel/resume/retry、无严格持久化 ToolCall sequence、tracked 示例模型 `supports_tools=false`、无真实 Provider 验收。无剩余阻塞项。 |

**结论：** `P2-M4-S4`～`S6`、Batch 11 和 Plan 2 M4 已完成，Codex self-review 与完整验证无阻塞问题。下一批可以进入 `P2-M5-S1`～`S3`，但本批没有实现 M5、Plan 3 或后续能力。没有使用 Claude Code、Fable 5、子代理或外部复审。

M4 完成后建议 commit：

```text
feat(frontend): show agent tool calls
```

---

## 7. Phase 5｜M5 测试、文档与封版

阶段目标：

```text
补齐 Plan 2 的测试、文档、截图、CHANGELOG 和 v0.2.0 tag，让它成为可回退、可展示的 Agent 初版。
```

阶段验收：

```text
1. Tool 抽象、Registry、安全边界、read_file、list_dir 都有测试
2. Agent Loop 和 Agent API 有核心路径测试
3. 前端 Tool Call 展示通过手动或 smoke 验证
4. README 和 docs 说明 Plan 2 新增能力与限制
5. CHANGELOG 记录 v0.2.0
6. 创建 v0.2.0 tag
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P2-M5-S1 | 补 Tool 抽象、Registry、校验、安全边界测试 | Codex | 后端测试 | `pytest` 对应测试通过 | Codex（done） |
| P2-M5-S2 | 补 read_file / list_dir / web_fetch 测试 | Codex | builtin tools 测试 | 正常、失败、安全场景通过 | Codex（done） |
| P2-M5-S3 | 补 Agent Loop / Agent API 测试 | Codex | Agent 测试 | mock 模型触发工具调用并返回最终答案 | Codex（done） |
| P2-M5-S4 | 补前端 Tool Call 展示检查 | Cursor | 前端类型检查、基础 UI 验证记录 | `npm run build` 或前端检查通过 | Codex（done） |
| P2-M5-S5 | 更新 README 和 Plan 2 文档 | Codex | README、`docs/10-tool-calling-design.md`、`docs/11-simple-agent-loop.md` | 文档说明工具限制和启动方式 | Codex（done） |
| P2-M5-S6 | 准备封版材料：截图、CHANGELOG、当前限制 | Cursor + Codex | Tool Call 截图、`CHANGELOG.md` | v0.2.0 功能边界清晰 | Codex（done） |
| P2-M5-S7 | Plan 2 全量 review 和修复 | Codex | review 记录、修复 commit | 后端测试和前端检查通过 | Codex final review（done） |
| P2-M5-S8 | 创建 v0.2.0 tag 并记录进入 Plan 3 的桥接状态 | Codex | `v0.2.0` tag、桥接检查表 | `git tag --list` 包含 v0.2.0 | 进行中（bridge done；tag 待用户手动创建） |

### P2-M5-S1～S3 Tool / Agent 测试加固验收记录（2026-07-19）

| 验收项 | 结果与证据 |
|---|---|
| 测试缺口矩阵 | 先建立“计划验收要求 → 已有测试 → 缺口 → 最小新测试”矩阵。Tool 抽象、Registry、read_file/list_dir 主路径、多轮 Agent Loop 和 Agent API 已有覆盖不重复新增；本批只补标准 JSON 参数、`.envrc`、`web_fetch` 延期边界和 builtin 安全失败的 API 闭环。 |
| S1 Tool / 参数 / 安全边界 | `validate_tool_arguments()` 现在以 `allow_nan=False` 拒绝 `NaN`/正负无穷，并返回不回显值的固定 `json` issue；共享路径策略按已记录的 `.env*` 边界拒绝 `.envrc`，read_file/list_dir 同步继承。 |
| S2 builtin 与 web_fetch 延期 | read_file/list_dir 测试覆盖 `.envrc` 拒绝和过滤。新增延期回归证明不存在 `app.tools.builtin.web_fetch` 模块、`WebFetchTool`/`web_fetch` export，caller-owned Registry 和 Provider schema 仍严格只有 `read_file`、`list_dir`；未增加网络实现、依赖或真实请求。 |
| S3 Agent Loop / API | 新增完整 Mock Provider + FastAPI + SimpleAgentService + builtin read_file + 临时 SQLite/工作区集成回归：读取合成 `.envrc` 被安全拒绝，failed ToolCall 与 observation 使用固定错误且不泄漏合成内容/绝对路径，Agent 随后返回最终文本并以 completed 201 持久化。 |
| TDD 证据 | 生产代码修改前聚焦 RED 为 `8 failed, 152 passed`：3 个非有限数、4 个 `.envrc` 工具边界和 1 个 Agent API 闭环按预期失败，`web_fetch` 缺席测试已通过；最小修复后 GREEN 为 `160 passed, 1 warning`，完整 Tool/Agent 聚焦为 `252 passed, 1 warning`。 |
| 完整验证 | Backend `451 passed, 1 warning`，warning 是已知 Starlette TestClient/httpx 弃用提示；`pip check` 无破损依赖。Frontend typecheck、`16 files / 79 tests`、production build（1812 modules transformed）通过；首次 build 的 ignored `dist/assets` EPERM 为受管沙箱限制，按已批准 build 权限重跑成功。 |
| SQLite 与边界检查 | 仅在新建系统临时目录使用 SQLite；Alembic `upgrade head`、`current --check-heads`、`check` 通过，head 为 `20260718_0003` 且临时目录已清理。70 个 Markdown 文件中的 45 个本地链接全部存在；11 个最终变更路径的真实 secret 模式、`web_fetch` runtime/file、依赖变更、用户数据库、tracked 生成物、后续 Plan runtime 和 staged path 均为 0；`git diff --check` 通过。 |
| Codex self-review | 必须修：非标准 JSON 数值与 `.envrc` 两个边界缺口已按 RED/GREEN 修复。后续 Step：M5-S4～S6 负责前端检查、正式文档同步和 release 截图；`docs/10`/`docs/11` 中 M4 后遗留的前端现状措辞在 S5 统一修正。接受限制：非流式、无 run list/polling/cancel/resume/retry、无严格持久化 ToolCall sequence、tracked 示例模型 `supports_tools=false`、无真实 Provider 验收、`web_fetch` 继续延期。不适用：migration、Provider 协议、Agent 状态、API 路由和前端 runtime 均无需修改。无剩余阻塞项。未使用 Claude Code、Fable 5、子代理或外部复审。 |

**结论：** `P2-M5-S1`～`S3` 与 Batch 12 已完成，Codex self-review 和完整验证无阻塞问题。下一批只能进入 `P2-M5-S4`～`S6`；本批没有开始 release 文档/截图、封版/tag、Plan 3 或后续能力。

S1～S3 建议 commit：

```text
test(agent): harden plan 2 tool and agent coverage
```

### P2-M5-S4～S6 前端检查与封版候选材料验收记录（2026-07-19）

| 验收项 | 结果与证据 |
|---|---|
| 验收缺口矩阵 | 先建立“计划要求 → 已有证据 → 当前缺口 → 最小补充”矩阵。S4 只刷新现有 ToolCall UI 自动化/浏览器证据，S5 修正 README 与 `docs/10`/`docs/11` 的 M4 过期措辞，S6 补正式脱敏截图、CHANGELOG 和限制；默认不改 runtime，不提前执行 S7 最终 review、S8 tag 或 Plan 3。 |
| S4 自动化检查 | Frontend typecheck 通过，完整 Vitest 为 `16 files / 79 tests`，production build 为 1812 modules transformed。未发现可复现的前端行为缺陷，因此 TDD 与 `frontend/src` 修改不适用，没有为了测试数新增重复用例。 |
| S4 Mock 浏览器验收 | 仅启动本地 Vite 与临时 Python 标准库 Mock API；未启动项目 backend、Provider 或 SQLite。合成 tools-capable 模型完成 `read_file("README.md")`，POST 返回 completed 201 并由 UI 写入 run UUID；刷新后 AgentRun/ToolCall 两个 GET 可恢复结果。1280×900 与 390×844 的 `documentElement.scrollWidth <= innerWidth` 均为 true；页面展示 final answer、Success、25ms、参数、结果摘要及 AgentRun/Conversation/Provider/database IDs。浏览器唯一 error 是现有开发页 `favicon.ico` 404，不影响功能或截图。 |
| S5 文档同步 | README/README_CN、overview、architecture、Tool Calling、Simple Agent 文档统一更新到 M5-S6；新增 `docs/13-plan-2-basic-agent.md` 汇总 pre-tag release boundary、启动/模型要求、安全、截图与限制。旧的“无 Agent API/前端”“下一批 M4/S1～S3”当前事实扫描为 0；正式版本仍写 `v0.1.0`，S7～S8 仍 pending。 |
| S6 封版候选材料 | 新增 `docs/assets/plan2/agent-tool-call-desktop.png`（71,737 bytes）与 `agent-tool-call-mobile.png`（57,120 bytes）；两图经目视检查只含合成 UUID、Mock 模型、`README.md` 与 localhost API。响应式验收使用 1280×900/390×844，文档图仅提高到 1280×1200/390×1600 以完整展示 ToolCall audit。CHANGELOG 仍在 `[Unreleased]`，没有伪造 0.2.0 release heading/date/tag。临时脚本、浏览器目录、Vite/Mock 进程与端口均已清理。 |
| 完整验证 | Backend `451 passed, 1 warning`，warning 是已知 Starlette TestClient/httpx 弃用提示；`pip check` 无破损依赖。Frontend typecheck、`16 files / 79 tests`、production build（1812 modules transformed）通过。全新系统临时 SQLite 的 Alembic `upgrade head`、`current --check-heads`、`check` 通过，head 为 `20260718_0003`，临时目录已清理。 |
| 文档、安全与 Plan 边界 | 74 个 Markdown 文件、60 个本地链接/图片、0 missing。最终 13 个变更路径的真实 secret 模式和行尾空白均为 0；`web_fetch` runtime/file、backend app、frontend src、依赖、用户数据库、staged path 与 `v0.2.0` tag 变更均为 0；无 Playwright 临时目录，`git diff --check` 通过，HEAD/origin/main 保持 `3154adb`。 |
| Codex self-review | 必须修：`docs/10`/`docs/11` 与 README/overview 的 M4 过期阶段措辞已修正，未发现 runtime must-fix。后续 Step：S7 执行全 Plan 2 review/修复，S8 才创建 tag 与完成 Plan 3 bridge。接受限制：同步非流式、无 run list/polling/cancel/resume/retry/并行 Tool、无严格持久化 ToolCall sequence、无 Agent-linked `LLMCall` usage、tracked 模型 `supports_tools=false`、无真实 Provider 验收、`web_fetch` 继续延期；开发页无 favicon 仅产生 404。 不适用：production frontend/backend、migration、Provider 协议、Agent 状态和 API schema 均无需修改。无剩余阻塞项，未使用 Claude Code、Fable 5、子代理或外部复审。 |

**结论：** `P2-M5-S4`～`S6` 与 Batch 13 已完成，Codex self-review 和完整验证无阻塞问题。下一批只能进入 `P2-M5-S7`～`S8`；当前没有执行最终 Plan review、创建 `v0.2.0` tag、完成 Plan 3 bridge 或实现后续能力。

S4～S6 建议 commit：

```text
docs(plan2): prepare basic agent release materials
```

### P2-M5-S7～S8 Plan 2 最终 review 与封版交接记录（2026-07-19）

| 验收项 | 结果与证据 |
|---|---|
| S7 全量 review | Codex 审查 `v0.1.0..b7a795c` 的完整 Plan 2 runtime、测试、迁移、API、前端与文档，而非只看本批 diff。检查覆盖 Tool/Registry/参数与路径安全、Provider Tool wire、Agent 最大步数/超时/失败、事务和复合外键、API 错误/查询、前端状态/URL gate、Plan 1 回归、secret/artifact 与 Plan 边界。正式记录见 `docs/reviews/2026-07-19-plan2-v0.2.0-final-review.md`。 |
| Must-fix 与 TDD | 发现 backend package、FastAPI OpenAPI、frontend package 和 lockfile 仍为 `0.1.0`。第一轮 RED 为 `1 failed`，修 backend 后 GREEN 为 `1 passed`；扩展前端断言后 RED 为 `1 failed, 1 passed`，最小修复后 GREEN 为 `2 passed`。四处版本现统一为 `0.2.0`，无其他 runtime must-fix。 |
| 完整验证 | Backend `453 passed, 1 warning`，warning 是已知 Starlette TestClient/httpx 弃用；`pip check` 无破损依赖。Frontend typecheck、`16 files / 79 tests`、production build（1812 modules transformed）通过。OpenAPI runtime 为 `0.2.0`，三个复数 Agent 路由存在、单数路由不存在。 |
| SQLite | 只在新建系统临时目录运行 Alembic `upgrade head`、`current --check-heads`、`check`，head 为 `20260718_0003` 且目录已清理。`backend/ai_agent_lab.db` 只读取文件元数据，验证前后均为 36,864 bytes、`2026-07-12 03:04:00 UTC`，未打开、迁移或修改。 |
| S8 Plan 3 bridge | Registry 可稳定注册后续 `search_knowledge_base`、ToolResult 四项表达能力、ToolCall 关联、read_file/list_dir 安全规则、Agent 最大步数/超时/失败返回五项均经当前代码、聚焦测试和全量门禁重新确认。没有创建 RAG/Qdrant/Knowledge 目录或实现 Plan 3 runtime。 |
| 文档与边界 | README 中英文、CHANGELOG、overview、architecture、Tool/Agent/API/release candidate 与本表同步到 S7 final-review-passed / S8 tag-pending 状态。77 个 Markdown、67 个本地链接/图片、0 missing，223 个候选文本路径 secret 命中 0；`web_fetch` runtime、later Plan 目录、migration 改动、tracked dist、临时 Playwright、staged path 和 `v0.2.0` tag 均为 0。最终 18 个路径仅含 release metadata/test/docs，唯一 runtime 路径是 FastAPI 版本号；没有真实 Provider、网络 Tool、`.env`、用户数据库内容、Claude Code、Fable 5、子代理或外部复审。 |
| Finding 分类 | 必须修：四处 release version metadata，已按 TDD 修复。后续 Step：用户手动 release commit、annotated `v0.2.0` tag 与 tag-target 复核。接受限制：Mock-only Provider、同步非流式/顺序 Tool、无 list/polling/cancel/resume/retry、无严格 sequence/Agent-linked LLMCall usage、字符级 observation 压缩、tracked 模型 tools=false、`web_fetch` 延期、editable-only Registry packaging、开发 favicon 404。不适用：新增 Agent 状态、ORM 字段、migration、Provider Tool 协议、API schema 或前端 runtime。 |

**发布后更新（2026-07-20）：** 用户已创建 release commit `0e3f3a6`、
annotated tag `v0.2.0` 并推送 `main`；Codex 已验证
`HEAD == origin/main == v0.2.0^{}`。`P2-M5-S8`、Batch 14 和 Plan 2 已完成。
上表中的 tag-pending 描述是 2026-07-19 收集证据时的历史状态。当前工作区准备
`v0.2.1` 发布后审计修复，既有 `v0.2.0` tag 不移动。

### Plan 2 v0.2.1 发布后审计修复记录（2026-07-20）

| 验收项 | 结果与证据 |
|---|---|
| Tool 与文件安全 | 标准 JSON、64 KiB arguments、4096 字符路径、私钥名称/内容、用户输入 symlink/reparse、目录有界枚举均按 RED/GREEN 加固；`web_fetch` 仍无 runtime、schema、Registry、依赖或网络实现。 |
| Agent 正确性 | `max_steps` 作为 ToolCall 尝试预算且 batch 原子拒绝；仅 `read_only` 可执行；未知、非法或非只读调用在持久化前清空参数；全 run timeout 会保留并终态化部分 Tool round；ToolCall 使用每 run 正序唯一 `sequence_index`。 |
| Registry 与前端 | 支持可选、本地、不含 secret 的模型 Registry 文件，空白环境值安全回退默认 Registry；Agent 页面用 `sessionStorage` 恢复迟到结果，URL 优先且 New task 清理；参数展示有界，字段明确为 Tool Call ID 和 Sequence。 |
| 完整验证 | Backend `503 passed, 1 warning`；`pip check` 无破损依赖。Frontend typecheck、`18 files / 90 tests`、production build（1813 modules）通过。新建系统临时 SQLite 升级到 `20260720_0004 (head)`，`current --check-heads` 与 `alembic check` 通过并已清理。 |
| Mock UI 与文档 | 仅用本地 Mock API/Vite 验证 POST、reload/GET restore、1280 desktop、390 mobile 和无横向溢出；两张正式脱敏截图已刷新。79 个 Markdown、67 个本地链接/图片、0 missing。 |
| 安全与边界 | 高置信凭据命中 0；私钥 marker 仅出现在预期安全代码、合成测试和修复计划；未读取真实 `.env`/secret/用户 SQLite 内容，未调用真实 Provider 或网络 Tool，未实现任何 Plan 3+ runtime。 |
| Codex self-review | must-fix 已全部按 TDD 修复；later Plan 保留 AgentStep/Trace/usage/replay、list/poll/cancel/resume/retry、Human Approval；接受同步非流式、顺序执行、Mock-only Provider、协作式取消和 `web_fetch` 延期；无阻塞项。 |
| Git/release 边界 | `HEAD == origin/main == v0.2.0^{}`，已发布标签不移动；staged paths 为 0，`v0.2.1` 标签不存在，由用户在手动提交后创建。 |

M5 完成后建议 commit：

```text
chore: release v0.2.0 basic agent
```

---

## 8. 每次执行 1～3 步的标准流程

每次让 Codex / Cursor 执行时，建议按这个模板下发：

```text
当前执行范围：P2-Mx-Sy ～ P2-Mx-Sz
必须遵守：只做这些 Step，不提前做 RAG、Memory、复杂 Runtime 或写文件工具
完成要求：
1. 实现对应交付物
2. 跑对应验证命令
3. 修复发现的问题
4. 更新必要文档
5. 给出变更摘要和测试结果
```

执行完成后，Codex review 使用这个检查表：

```text
1. 是否只改了本批次相关文件
2. 是否引入超出 Plan 2 的能力
3. 是否破坏 Plan 1 的 Chat / Streaming / 会话历史
4. Tool 安全边界是否仍然有效
5. 是否有测试或手动验证证据
6. 是否同步 README / docs / env example
7. 是否适合进入下一批次
```

---

## 9. Review 节点

每批和每个里程碑只执行 Codex self-review，不请求、运行或等待 Claude Code。M1、M3 和 M5 的重点如下：

| 节点 | 审核重点 | 输入材料 |
|---|---|---|
| M1 结束 | Tool 抽象、Registry、安全边界是否能支撑后续工具 | diff、Tool 类型、Registry、security 代码、测试结果 |
| M3 结束 | Provider tools 接口和 Simple Agent Loop 是否稳定 | diff、Agent Loop、Provider 改动、ToolCall 记录、测试结果 |
| M5 封版前 | v0.2.0 是否能作为 Plan 3 的工具底座 | 全量 diff、README、测试结果、CHANGELOG、桥接检查 |

Codex review 后：

```text
1. 判断哪些意见必须修
2. 拆成 1～3 个修复 Step
3. 修复后重新跑测试
4. 更新文档和 changelog
```

全部 6 个 Plan 和整个项目完成后，再由用户决定是否使用 Fable 5 做一次全项目检查；项目完成前不请求 Fable 5，也不得虚构任何外部复审结果。

---

### P2-M1/M2 独立审计修复记录（2026-07-18）

| 修复项 | 结果与证据 |
|---|---|
| 本地文件安全 | `list_dir` 通过 Windows reparse-point 属性识别 junction，只以 `symlink` 类型报告且不递归；新增常见包管理器、Git、云、容器和 Kubernetes 凭据路径拒绝策略。合成凭据和 junction 测试不读取真实敏感文件。 |
| Tool / Registry 契约 | Tool 名称、描述、权限级别、超时和参数 schema 改为只读定义；schema 读取为深拷贝。注册 schema 必须具有 JSON 可序列化的 object 根，Tool 名称符合最多 64 字符的 Provider function 边界。 |
| Agent 审计一致性 | 新增线性 migration `20260718_0003`，以 Message `(id, conversation_id)` 唯一键和 AgentRun 复合外键拒绝跨 Conversation 关联；旧 revision 中若已有跨会话或悬空关联则升级安全停止且不回显内容。 |
| 正确性与文档 | `list_dir` 只有确实存在未返回条目时才标记截断；README/README_CN、CHANGELOG、Tool Calling 设计和本验收清单同步当前事实。 |
| TDD 与完整验证证据 | 文件安全测试为 `107 passed`，Tool/Registry/validation 为 `49 passed`，Agent ORM 为 `10 passed`，迁移套件为 `6 passed`。完整 Backend 为 `308 passed, 1 warning`；`pip check`、Frontend typecheck、8 files / 37 tests、production build、全新临时 SQLite 升级/检查/降级/再升级和无 Provider FastAPI smoke 均通过。 |

该记录修复独立审计发现，不实现 Provider tools、Agent Loop、Agent API、前端 Tool Call 或任何后续 Plan 能力。Codex self-review 和完整验证均无阻塞项；依据 2026-07-18 用户决定，不再执行 Claude Code secondary review，可以进入 P2-M3-S1～S3。全部 6 个 Plan 和整个项目完成前不请求 Fable 5，也不得虚构任何外部复审结果。

---

## 10. Plan 2 最终验收清单

| 验收项 | 状态 | 证据 |
|---|---|---|
| Tool 抽象完成 | done（M1） | Tool base 代码和测试 |
| Tool Registry 完成 | done（M1） | Registry 测试 |
| read_file 可用 | done（M2） | read_file 正常、限制和安全测试 |
| list_dir 可用 | done（M2） | list_dir 正常、junction、限制和安全测试 |
| 工具参数校验可用 | done（M1 / v0.2.1 audit fix） | Draft 2020-12、object 根、标准 JSON、64 KiB 参数和 4096 字符路径测试 |
| 工具安全边界可用 | done（M1/M2 / v0.2.1 audit fix） | 路径、凭据/私钥名称与内容、无 symlink/junction traversal、有界枚举测试 |
| LLM Provider 支持 tools | done（M3 S1～S3，非流式协议） | Provider contract、schema adapter、OpenAI-compatible mock 测试；真实模型能力仍为 false |
| Simple Agent Loop 可用 | done（M3 S4～S8 / v0.2.1 audit fix） | 直接回答、多轮 Tool、原子 ToolCall 预算、权限拒绝、单 Tool/全 run 超时、失败和持久化测试 |
| Agent API 可用 | done（M4 S1～S3，后端同步 API） | create/query、Tool round、结构化失败、错误与事务测试 |
| 工具调用记录可保存 | done（M1 schema / M3 S6～S8 / v0.2.1 sequence） | AgentRun/ToolCall ORM、迁移、正序唯一 `sequence_index`、执行状态和 commit/reload 测试 |
| 前端能展示 Tool Call | done（M4 S4～S6 / M5 S4～S6 / v0.2.1 DOM tests） | 组件与 mounted async 测试、本地 mock 桌面/移动浏览器验收与正式脱敏 release 截图 |
| 工具失败不会导致系统崩溃 | done（M1/M2/M3 S7） | Tool validation、内置 Tool、timeout 和安全 observation 测试 |
| README 已更新 | done（through v0.2.1 candidate） | README / README_CN 当前范围、Agent 工作台、本地 Registry、启动要求、截图与限制说明 |
| docs 已更新 | done（through v0.2.1 candidate） | Provider、Tool Calling、Simple Agent、Agent API、release、架构文档与验收记录 |
| Plan 2 全量 review 已完成 | done（M5 S7） | Codex final review、release version RED/GREEN、完整 Backend/Frontend/SQLite/边界验证 |
| 已创建 v0.2.0 tag | done（2026-07-20 verified） | annotated tag object `3f727e3`；peeled target `0e3f3a66e1322c565f2056696f7e482cedbb5f6c` |

---

## 11. Plan 2 到 Plan 3 的桥接检查

只有下面 5 项都满足，才建议进入 Plan 3：

| 桥接项 | 状态 | 说明 |
|---|---|---|
| Tool Registry 可以稳定注册后续 `search_knowledge_base` 工具 | done（S7 fresh review） | caller-owned Registry、顺序、schema adapter 与重复/原子失败测试稳定；Plan 3 不需要重写工具体系 |
| ToolResult 结构能表达 success、content、error、metadata | done（S7 + v0.2.1 audit） | 成功、失败、结构化 data/metadata、标准 JSON 和 observation 压缩测试 |
| 工具调用日志能关联 conversation_id 或 agent_run_id | done（S7 + v0.2.1 audit） | ToolCall 复合外键、AgentRun/Conversation 归属、strict sequence 和 commit/reload 测试 |
| read_file / list_dir 的路径安全规则已经固定 | done（S7 + v0.2.1 audit） | traversal、敏感/私钥、无 link traversal、大小/深度/条目/枚举限制与正式文档 |
| Simple Agent Loop 有最大步数、超时和失败返回 | done（S7 + v0.2.1 audit） | 默认 3 个 ToolCall、原子 batch、Tool/全 run timeout、权限边界、结构化 failed AgentRun 和完整回归 |

---

## 12. 推荐文件位置

执行过程中建议把相关产物放在这些位置：

| 类型 | 路径 |
|---|---|
| Tool 抽象 | `backend/app/tools/base.py` |
| Tool Registry | `backend/app/tools/registry.py` |
| Tool 安全边界 | `backend/app/tools/security.py` |
| 内置工具 | `backend/app/tools/builtin/` |
| Agent Loop | `backend/app/agents/simple_agent.py` |
| Agent API | `backend/app/api/v1/agents.py` |
| 数据模型 | `backend/app/models/agent_run.py`、`backend/app/models/tool_call.py` |
| 后端测试 | `backend/tests/tools/`、`backend/tests/agents/` |
| 前端 Agent API | `frontend/src/api/agent.ts` |
| 前端 Tool Call 组件 | `frontend/src/components/agent/` 或 `frontend/src/components/chat/` |
| 项目文档 | `docs/10-tool-calling-design.md`、`docs/11-simple-agent-loop.md`、`docs/12-agent-api.md` |
| 截图 | `docs/assets/plan2/` |

---

## 13. 执行建议

Plan 2 的重点不是让 Agent 很聪明，而是让工具调用链条安全、可追踪、可复用。

推荐实际推进方式：

```text
先做 Tool 抽象和安全边界
再做 read_file / list_dir
再扩展 Provider tools
再实现 Simple Agent Loop
最后做 API、前端展示、测试、文档和封版
```

不要在 Plan 2 阶段提前做复杂 Agent Runtime。

Plan 2 做稳之后，Plan 3 的 `search_knowledge_base` 才能自然作为新工具接入，而不是另起一套 RAG 调用体系。
