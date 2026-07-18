# Plan 2 执行步骤表｜Tool Calling + 简单 Agent Loop

> 适用文档：`00-ALL PLAN/02-PLAN-2 (V1.0).md`  
> 执行方式：每次只领取连续 1～3 个 Step，完成后立即测试、提交、review。  
> 阶段目标：一个阶段完成一个里程碑；一个里程碑通过后再进入下一个里程碑。

---

## 0. 执行总原则

| 规则 | 说明 |
|---|---|
| 单次执行范围 | Cursor / Codex 每次只做 1～3 个连续 Step |
| 执行顺序 | 必须按 `P2-Mx-Sy` 顺序推进，除非 Codex 明确调整 |
| 每步完成定义 | 代码可运行、局部测试通过、相关文档或配置同步 |
| 每个阶段完成定义 | 阶段验收项全部通过，Codex review 后进入下一阶段 |
| Claude Code 使用时机 | Tool 抽象、工具安全边界、Provider tools 支持、Agent Loop 完成后 |
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
| Phase 1 | M1 Plan 1 交接与 Tool 地基 | Step 1～5 | v0.1.0 检查、Tool 抽象、Registry、参数校验、安全边界 | 15～25 h | Codex | Codex + Claude Code |
| Phase 2 | M2 内置只读工具 | Step 6～8 | read_file、list_dir、可选 web_fetch | 10～20 h | Codex | Codex review |
| Phase 3 | M3 LLM Tools 与 Agent Loop | Step 9～10 | Provider tools 参数、Simple Agent Loop、最大步数和失败处理 | 15～25 h | Codex | Codex + Claude Code |
| Phase 4 | M4 Agent API 与前端展示 | Step 11～12 | Agent API、Tool Call 前端展示 | 10～20 h | Codex + Cursor | Codex review |
| Phase 5 | M5 测试、文档与封版 | Step 13～15 | Tool / Agent 测试、文档、CHANGELOG、v0.2.0 tag | 10～15 h | Codex + Cursor | Codex + Claude Code |

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
| Batch 7 | P2-M3-S1～S3 | 扩展 LLM Provider 支持 tools | Provider mock 测试 | 未完成 |
| Batch 8 | P2-M3-S4～S6 | 实现 Simple Agent Loop | Agent mock 测试 | 未完成 |
| Batch 9 | P2-M3-S7～S8 | 完成失败处理、最大步数、工具结果压缩雏形 | Codex + Claude review M3 | 未完成 |
| Batch 10 | P2-M4-S1～S3 | 实现 Agent API 和 Tool Call 查询 | API 测试 | 未完成 |
| Batch 11 | P2-M4-S4～S6 | 前端展示 Agent Run 和 Tool Call | 浏览器手测 | 未完成 |
| Batch 12 | P2-M5-S1～S3 | 补 Tool / Agent 测试 | 后端测试 | 未完成 |
| Batch 13 | P2-M5-S4～S6 | 补文档、README、截图和限制说明 | 文档 review | 未完成 |
| Batch 14 | P2-M5-S7～S8 | 最终 review、修复、v0.2.0 封版 | Codex + Claude final review | 未完成 |

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
| P2-M3-S1 | 扩展 LLMProvider `chat` 接口支持 tools | Codex | Provider base interface 更新 | mock provider 可接收 tools 参数 | Claude Code 可审 |
| P2-M3-S2 | 扩展 OpenAI-compatible Provider 的 tool calling 请求和响应解析 | Codex | provider tool call 支持 | mock response 能解析 tool call | Codex |
| P2-M3-S3 | 实现 Tool Schema 转换为模型可用格式 | Codex | tool schema adapter | read_file / list_dir schema 可序列化 | Codex |
| P2-M3-S4 | 创建 Simple Agent Loop 基础流程 | Codex | `backend/app/agents/simple_agent.py` | 无工具任务直接返回答案 | Codex |
| P2-M3-S5 | 接入工具选择、执行和 observation 回填 | Codex | Agent 调用 Tool Registry | 固定 mock 模型触发 read_file 后生成最终答案 | Codex |
| P2-M3-S6 | 持久化 AgentRun 和 ToolCall | Codex | Agent run service | 每次工具调用都有数据库记录 | Codex |
| P2-M3-S7 | 实现最大步数、超时、失败返回 | Codex | runtime policy 常量或配置 | 超过最大步数返回可读错误 | Claude Code 可审 |
| P2-M3-S8 | 完成 M3 review 和 Agent Loop 文档 | Codex | `docs/11-simple-agent-loop.md` | 文档解释 Agent Loop 流程和限制 | Codex + Claude review |

M3 完成后建议 commit：

```text
feat(agent): add simple tool calling loop
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
| P2-M4-S1 | 实现 Agent API 请求 / 响应 schema | Codex | `backend/app/schemas/agent.py` | schema 测试通过 | Codex |
| P2-M4-S2 | 实现 `POST /api/v1/agent/runs` | Codex | `backend/app/api/v1/agent.py` | API 测试可启动 Agent Run | Codex |
| P2-M4-S3 | 实现 Agent Run 查询和 Tool Call 查询接口 | Codex | `GET /agent/runs/{id}`、`GET /agent/runs/{id}/tool-calls` | API 测试通过 | Codex |
| P2-M4-S4 | 创建前端 agent API 封装和类型 | Cursor | `frontend/src/api/agent.ts`、`types/agent.ts` | TypeScript 检查通过 | Codex |
| P2-M4-S5 | 实现 Tool Call 展示组件 | Cursor | `ToolCallCard.tsx`、`ToolCallTimeline.tsx` | 组件可展示 pending / success / error | Codex |
| P2-M4-S6 | 在 Chat 页面或 Agent 页面接入 Agent Run 展示 | Cursor + Codex | Agent 任务输入、结果展示、工具调用过程 | 浏览器手测 README 总结场景 | Codex review |

M4 完成后建议 commit：

```text
feat(agent): add agent api and tool call UI
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
| P2-M5-S1 | 补 Tool 抽象、Registry、校验、安全边界测试 | Codex | 后端测试 | `pytest` 对应测试通过 | Codex |
| P2-M5-S2 | 补 read_file / list_dir / web_fetch 测试 | Codex | builtin tools 测试 | 正常、失败、安全场景通过 | Codex |
| P2-M5-S3 | 补 Agent Loop / Agent API 测试 | Codex | Agent 测试 | mock 模型触发工具调用并返回最终答案 | Codex |
| P2-M5-S4 | 补前端 Tool Call 展示检查 | Cursor | 前端类型检查、基础 UI 验证记录 | `npm run build` 或前端检查通过 | Codex |
| P2-M5-S5 | 更新 README 和 Plan 2 文档 | Codex | README、`docs/10-tool-calling-design.md`、`docs/11-simple-agent-loop.md` | 文档说明工具限制和启动方式 | Codex |
| P2-M5-S6 | 准备封版材料：截图、CHANGELOG、当前限制 | Cursor + Codex | Tool Call 截图、`CHANGELOG.md` | v0.2.0 功能边界清晰 | Codex |
| P2-M5-S7 | Plan 2 全量 review 和修复 | Codex + Claude Code | review 记录、修复 commit | 后端测试和前端检查通过 | Codex + Claude |
| P2-M5-S8 | 创建 v0.2.0 tag 并记录进入 Plan 3 的桥接状态 | Codex | `v0.2.0` tag、桥接检查表 | `git tag --list` 包含 v0.2.0 | Codex final review |

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

## 9. Claude Code Review 节点

Claude Code 不需要每个 Step 都参与，建议在这些节点使用：

| 节点 | 审核重点 | 输入材料 |
|---|---|---|
| M1 结束 | Tool 抽象、Registry、安全边界是否能支撑后续工具 | diff、Tool 类型、Registry、security 代码、测试结果 |
| M3 结束 | Provider tools 接口和 Simple Agent Loop 是否稳定 | diff、Agent Loop、Provider 改动、ToolCall 记录、测试结果 |
| M5 封版前 | v0.2.0 是否能作为 Plan 3 的工具底座 | 全量 diff、README、测试结果、CHANGELOG、桥接检查 |

Claude Code 审核后，Codex 负责：

```text
1. 判断哪些意见必须修
2. 拆成 1～3 个修复 Step
3. 修复后重新跑测试
4. 更新文档和 changelog
```

---

## 10. Plan 2 最终验收清单

| 验收项 | 状态 | 证据 |
|---|---|---|
| Tool 抽象完成 | pending | Tool base 代码和测试 |
| Tool Registry 完成 | pending | Registry 测试 |
| read_file 可用 | pending | read_file 测试或手动结果 |
| list_dir 可用 | pending | list_dir 测试或手动结果 |
| 工具参数校验可用 | pending | schema 校验测试 |
| 工具安全边界可用 | pending | 路径安全测试 |
| LLM Provider 支持 tools | pending | Provider mock 测试 |
| Simple Agent Loop 可用 | pending | Agent Loop 测试 |
| Agent API 可用 | pending | API 测试 |
| 工具调用记录可保存 | pending | tool_calls 数据库记录 |
| 前端能展示 Tool Call | pending | 页面截图 |
| 工具失败不会导致系统崩溃 | pending | 失败场景测试 |
| README 已更新 | pending | README 链接 |
| docs 已更新 | pending | docs 链接 |
| 已创建 v0.2.0 tag | pending | `git tag --list` 输出 |

---

## 11. Plan 2 到 Plan 3 的桥接检查

只有下面 5 项都满足，才建议进入 Plan 3：

| 桥接项 | 状态 | 说明 |
|---|---|---|
| Tool Registry 可以稳定注册后续 `search_knowledge_base` 工具 | pending | Plan 3 不需要重写工具体系 |
| ToolResult 结构能表达 success、content、error、metadata | pending | RAG 工具需要返回来源和检索 metadata |
| 工具调用日志能关联 conversation_id 或 agent_run_id | pending | Plan 3 的 RAG Tool 可以被追踪 |
| read_file / list_dir 的路径安全规则已经固定 | pending | 文档解析和项目文件读取共用安全边界 |
| Simple Agent Loop 有最大步数、超时和失败返回 | pending | 后续 RAG Tool 失败时不会拖垮 Agent |

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
| Agent API | `backend/app/api/v1/agent.py` |
| 数据模型 | `backend/app/models/agent_run.py`、`backend/app/models/tool_call.py` |
| 后端测试 | `backend/tests/tools/`、`backend/tests/agents/` |
| 前端 Agent API | `frontend/src/api/agent.ts` |
| 前端 Tool Call 组件 | `frontend/src/components/agent/` 或 `frontend/src/components/chat/` |
| 项目文档 | `docs/10-tool-calling-design.md`、`docs/11-simple-agent-loop.md` |
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
