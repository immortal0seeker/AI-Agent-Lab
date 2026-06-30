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
| Batch 1 | P2-M1-S1～S3 | 确认 Plan1 地基，建立 Tool 核心结构 | 跑现有测试，提交 Tool 抽象 | 未完成 |
| Batch 2 | P2-M1-S4～S6 | 实现 Registry、参数校验和安全策略雏形 | Tool 单元测试 | 未完成 |
| Batch 3 | P2-M1-S7～S8 | 持久化 AgentRun / ToolCall，完成 M1 review | Codex + Claude review M1 | 未完成 |
| Batch 4 | P2-M2-S1～S3 | 实现 read_file 并覆盖路径安全测试 | 工具测试 | 未完成 |
| Batch 5 | P2-M2-S4～S6 | 实现 list_dir 和工具注册 | 工具集成测试 | 未完成 |
| Batch 6 | P2-M2-S7 | 可选实现 web_fetch 或明确延期记录 | Codex review M2 | 未完成 |
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
| P2-M1-S1 | 检查 Plan 1 封版状态和 v0.1.0 tag | Codex | Plan 1 验收记录 | 后端、前端、Chat、Streaming 均可启动或有明确证据 | Codex |
| P2-M1-S2 | 创建 Tool 模块目录和基础类型 | Codex | `backend/app/tools/base.py`、`Tool`、`ToolResult`、`ToolError` | Tool 类型测试通过 | Codex |
| P2-M1-S3 | 定义 ToolCall 请求 / 响应 schema | Codex | `backend/app/schemas/tool.py` | Pydantic schema 测试通过 | Codex |
| P2-M1-S4 | 实现 Tool Registry | Codex | `backend/app/tools/registry.py` | 注册、查找、重复注册测试通过 | Codex |
| P2-M1-S5 | 实现工具参数校验 | Codex | JSON Schema 或 Pydantic 校验逻辑 | 缺参、类型错误、未知参数测试通过 | Codex |
| P2-M1-S6 | 实现只读路径安全边界 | Codex | `backend/app/tools/security.py` | 禁止读取 `.env`、目录穿越、工作区外路径测试通过 | Claude Code 可审 |
| P2-M1-S7 | 创建 `agent_runs` 和 `tool_calls` ORM 模型与迁移 | Codex | `backend/app/models/agent_run.py`、`tool_call.py` | 数据库迁移和模型测试通过 | Codex |
| P2-M1-S8 | 完成 M1 review 和文档记录 | Codex | `docs/10-tool-calling-design.md` 初版 | 文档说明 Tool 抽象、Registry、权限边界 | Codex + Claude review |

M1 完成后建议 commit：

```text
feat(tools): add tool abstractions registry and safety boundary
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
| P2-M2-S1 | 实现 read_file 工具 | Codex | `backend/app/tools/builtin/read_file.py` | 可读取 README，返回文本内容和 metadata | Codex |
| P2-M2-S2 | 为 read_file 添加安全和异常测试 | Codex | read_file 测试 | `.env`、二进制文件、超大文件、目录穿越均被拒绝或安全处理 | Codex |
| P2-M2-S3 | 将 read_file 注册到 Tool Registry | Codex | builtin tool 初始化逻辑 | Registry 能列出 read_file | Codex |
| P2-M2-S4 | 实现 list_dir 工具 | Codex | `backend/app/tools/builtin/list_dir.py` | 可列出项目内目录，返回文件名、类型、大小 | Codex |
| P2-M2-S5 | 为 list_dir 添加安全和异常测试 | Codex | list_dir 测试 | 工作区外路径、隐藏敏感文件、无权限路径安全处理 | Codex |
| P2-M2-S6 | 将 list_dir 注册到 Tool Registry 并补工具列表测试 | Codex | builtin tools registry 测试 | Registry 能列出 read_file / list_dir | Codex |
| P2-M2-S7 | 评估并处理 web_fetch：实现低风险版本或记录延期 | Codex | `web_fetch.py` 或 docs 限制说明 | 若实现则普通网页文本抓取测试通过；若延期则 README 说明 | Codex review |

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
