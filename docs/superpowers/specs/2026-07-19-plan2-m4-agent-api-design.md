# Plan 2 M4 Agent API Design

## 1. Scope

本设计只覆盖 `P2-M4-S1～S3`：

- `S1`：定义 Agent API 请求、AgentRun 响应和 ToolCall 响应 schema。
- `S2`：实现同步执行 `POST /api/v1/agents/runs`。
- `S3`：实现 AgentRun 与所属 ToolCall 查询接口。

本批不实现前端 Agent API 封装、Tool Call 组件或页面接入；这些属于
`P2-M4-S4～S6`。本批也不改变 M3 Simple Agent Loop、ORM 状态机或数据库
migration，不实现流式 Tool Calling、自动 retry、cancel/resume、并行 Tool、
RAG、Embedding、Memory、MCP、Shell Tool、文件写入/删除或后续 Plan 能力。

## 2. Chosen Architecture

采用复数资源路由与薄 Route：

```text
POST /api/v1/agents/runs
GET  /api/v1/agents/runs/{run_id}
GET  /api/v1/agents/runs/{run_id}/tool-calls
        -> API schema validation
        -> AgentService / SimpleAgentService
        -> SQLAlchemy Session
        -> API response schema
```

源计划 Step 11 使用复数 `/agents/runs`，而执行步骤表曾写成单数
`/agent/runs`。本批统一采用复数形式，使它与现有 `/conversations`、
`/models` 资源路由一致；不保留单数兼容别名，避免重复且含糊的 API 表面。

新增 `app.services.agent_service.AgentService`，负责：

- 按 ID 读取 AgentRun，并把不存在映射为稳定领域异常；
- 校验 AgentRun 存在后，按确定性顺序读取其 ToolCall；
- 接受已注入的 `SimpleAgentService` 执行器来启动运行，但不复制 Agent Loop。

`SimpleAgentService` 继续独占 Provider 决策、Tool 执行、状态流转和运行结果。
API route 只做请求转换、调用 service 和响应转换。数据库依赖继续统一负责请求
级 commit/rollback；所有 service 只 flush，不自行 commit。

## 3. Request Contract

新增 `AgentRunCreate`：

| Field | Rule |
|---|---|
| `conversation_id` | 可选现有 Conversation UUID；省略时创建 Conversation |
| `provider` | 去除首尾空白后非空，最长 100 |
| `model` | 去除首尾空白后非空，最长 255 |
| `input` | 非空且不能全为空白，作为 Agent goal |
| `temperature` | `0..2`，默认 `0.7` |
| `max_tokens` | 可选正整数 |
| `max_steps` | 严格整数 `1..10`，默认 `3` |

Schema 使用 `extra="forbid"`，拒绝未知字段。外部字段使用源计划中的 `input`，
`AgentService` 将其显式转换为内部 `SimpleAgentRequest.content`；不同时接受
`content` 别名，保证 OpenAPI 契约唯一。

## 4. Response Contracts

### 4.1 AgentRun

`AgentRunRead` 暴露：

- `id`
- `conversation_id`
- `user_message_id`
- `status`
- `goal`
- `final_answer`
- `error`
- `started_at`
- `ended_at`
- `latency_ms`
- `created_at`

`status` 复用现有 ORM 允许值：`created`、`running`、`waiting_tool`、
`completed`、`failed`、`cancelled`。虽然同步 POST 正常只会返回 terminal 状态，
查询 schema 必须能读取数据库允许的全部状态。API 字段 `error` 显式映射 ORM
字段 `error_message`。

`AgentRunExecutionRead` 在上述字段基础上增加 `tool_calls`。POST 使用该 schema，
从而在一次响应中返回阶段验收要求的 final answer、Tool Calls、status 和 error。

### 4.2 ToolCall

`ToolCallRead` 暴露：

- `id`
- `tool_call_id`
- `agent_run_id`
- `conversation_id`
- `tool_name`
- `arguments`
- `result`
- `status`
- `error`
- `started_at`
- `ended_at`
- `latency_ms`
- `created_at`

API 字段 `arguments`、`result`、`error` 分别显式映射 ORM 的
`arguments_json`、`result_json`、`error_message`。`result` 使用现有
`ToolResult | None`，因此 schema 会验证持久化结果的结构。ToolCall status 复用
现有 `pending`、`running`、`success`、`failed`、`timeout`、`blocked`。

POST 响应中的 ToolCall 保持 `SimpleAgentResult.tool_calls` 的实际执行顺序。
查询接口按 `created_at ASC, id ASC` 返回确定性顺序。数据库仍没有独立 sequence
字段，本批不把该顺序描述为严格的可重放 step 序列。

## 5. Endpoint Semantics

### 5.1 Create Agent Run

```text
POST /api/v1/agents/runs -> 201 Created
```

流程：

1. Pydantic 校验 `AgentRunCreate`。
2. API 依赖构造 Model Registry、Provider mapping 和只读 Tool Registry。
3. Tool Registry 只注册 `read_file` 与 `list_dir`，沿用现有 workspace root、
   路径拒绝、敏感名称和资源上限。
4. AgentService 将 API 请求转换为 `SimpleAgentRequest` 并调用现有执行器。
5. 完成或结构化失败结果都转换为 `AgentRunExecutionRead`。
6. 请求数据库依赖在响应交付前提交 Conversation、Messages、AgentRun 和
   ToolCalls；提交失败不得返回伪成功。

如果 AgentRun 已创建但 M3 运行以 `status="failed"` 结束，例如 Provider timeout、
Provider failure、空白终态或达到 `max_steps`，POST 仍正常提交并返回 `201`。
客户端通过 `status` 与安全 `error` 判断业务结果，并能随后查询该失败运行。

### 5.2 Get Agent Run

```text
GET /api/v1/agents/runs/{run_id} -> AgentRunRead
```

该接口只读取已持久化 AgentRun，不初始化 Provider、Tool Registry 或真实外部
连接。未知 UUID 对应稳定 404；格式错误 UUID 由统一校验错误返回 422。

### 5.3 List Tool Calls

```text
GET /api/v1/agents/runs/{run_id}/tool-calls -> list[ToolCallRead]
```

Service 先确认 AgentRun 存在，再查询所属 ToolCall。已存在但没有 ToolCall 的
运行返回 `200 []`；未知 AgentRun 返回 404，而不是无法区分的空列表。该接口同样
不得初始化 Provider。

## 6. Dependency and Transaction Boundaries

新增依赖：

- `get_tool_registry()`：按请求构造新的 `ToolRegistry` 并注册现有只读内置 Tool，
  避免跨请求共享可变 Registry。
- `get_simple_agent_service()`：仅供 POST，组合当前 Session、Model Registry、
  Provider mapping 和 Tool Registry。
- `get_agent_service()`：只依赖当前 Session；GET 查询因此在没有 Provider key 时
  仍可工作。POST 把注入的 `SimpleAgentService` 传给该 service。

`get_db_session()` 保持现有语义：正常返回路径 commit，异常路径 rollback。结构化
failed AgentRun 是正常返回路径，因此会提交。请求校验、模型/Provider/Conversation
等 preflight 异常发生在 AgentRun 创建前并触发 rollback。SQLAlchemy 异常继续由
统一错误边界映射并脱敏。

## 7. Error Mapping

新增 Agent 领域错误映射：

| Condition | HTTP | Code |
|---|---:|---|
| Agent model 不存在 | 400 | `model_not_found` |
| Agent model 不支持 Tools | 400 | `model_tools_unsupported` |
| Provider 未配置 | 503 | `provider_unavailable` |
| Conversation 不存在 | 404 | `conversation_not_found` |
| AgentRun 不存在 | 404 | `agent_run_not_found` |
| 请求字段或 UUID 非法 | 422 | `validation_error` |
| 数据库错误 | 503 | `database_error` |

响应不包含 Provider exception、API key、配置值、绝对路径、SQL 文本或 stack trace。
M3 已结构化的运行时错误继续作为 AgentRun `error` 返回，而不再次转换成 HTTP
错误。任务取消与数据库失效事务仍传播到请求级边界，不伪造已提交记录。

## 8. Testing Strategy

严格按 RED -> GREEN 覆盖：

1. Schema 默认值、严格 `max_steps`、未知字段、空白 `input`、状态与 ToolResult
   映射。
2. OpenAPI 暴露三个复数路由，且没有单数兼容别名。
3. Mock Provider 直接回答：POST 201、Conversation/User/Assistant/AgentRun 持久化，
   响应 final answer 与状态正确。
4. Mock Provider 请求 Tool 后回答：使用临时 workspace 和只读 Tool，POST 返回并
   持久化完整 ToolCall；不得访问真实敏感文件。
5. 结构化 failed AgentRun：POST 仍为 201，失败记录和已执行 ToolCall 可 commit、
   reload、查询。
6. Preflight model/tools/provider/conversation 错误：统一安全 HTTP 响应，数据库不留
   部分记录。
7. GET run、GET empty/non-empty Tool Calls、确定性排序、未知 run 404、非法 UUID
   422。
8. 明确证明两个 GET 查询不解析或初始化 Provider 配置。
9. 数据库 commit/查询失败使用统一错误响应，不返回伪成功或私有诊断。
10. Plan 1 Chat/Streaming、M3 Simple Agent、Tool 安全和 migration 回归。

所有验收使用 Mock Provider、临时 SQLite、临时受控目录与 FastAPI TestClient。
不读取真实 `.env`、凭据或用户数据库，不调用真实/付费 Provider 或网络 Tool。

## 9. Documentation and Review Gate

实现完成后同步：

- `docs/11-simple-agent-loop.md`：把“无 Agent API”更新为当前 API 契约与仍未实现
  的前端限制。
- `docs/01-architecture.md`、README 中英文与 CHANGELOG：记录 Agent API 和查询
  表面，但不宣称前端已完成。
- Plan 2 执行步骤表：只标记 Batch 10、S1～S3 和实际验证证据；下一批保持
  `P2-M4-S4～S6`。
- 必要的 API 正式文档：字段、状态、失败提交语义和 Tool result 安全边界。

最终 Gate：

- Backend 完整 pytest 与 `pip check` 通过。
- Frontend typecheck、完整 Vitest 与 production build 回归通过，即使本批不改
  frontend。
- 全新临时 SQLite 通过 Alembic `upgrade head`、`current --check-heads` 和
  `alembic check`；绝不触碰用户数据库。
- FastAPI health/OpenAPI/request-id 与 Agent API mock smoke 通过。
- 文档链接、秘密模式、生成物、Plan 边界、`git diff --check` 和 status 通过。
- Codex self-review 无阻塞问题；不使用 Claude Code、Fable 5 或子代理。

本批完成后只能进入 `P2-M4-S4～S6`，不得提前开始 M5 或 Plan 3。
