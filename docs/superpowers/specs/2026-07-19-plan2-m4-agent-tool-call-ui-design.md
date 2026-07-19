# Plan 2 M4 Agent Tool Call UI Design

## 1. Scope

本设计只覆盖 `P2-M4-S4～S6`：

- `S4`：创建前端 Agent API 封装和 TypeScript 类型。
- `S5`：实现 ToolCall 卡片和时间线组件。
- `S6`：在独立 Agent 工作区接入任务输入、运行结果和 ToolCall 过程。

本批复用已经完成的同步 Agent API：

```text
POST /api/v1/agents/runs
GET  /api/v1/agents/runs/{run_id}
GET  /api/v1/agents/runs/{run_id}/tool-calls
```

本批不改变后端 Agent 状态、ORM、迁移、Provider、Tool Registry 或路径安全策略，
不实现 AgentRun 列表、流式 ToolCall、轮询、取消、恢复、自动重试、并行 Tool、
RAG、Embedding、Memory、MCP、Shell Tool、文件写入/删除或后续 Plan 能力。

## 2. Chosen User Experience

采用独立 Agent 工作区，而不是把同步 Agent 生命周期嵌入现有流式 Chat 状态机。
侧栏提供 `Chat` 与 `Agent` 两个工作区入口：

- 默认仍进入 Chat，Plan 1 的流式 Chat、停止生成、会话恢复和历史列表保持原样。
- Agent 工作区只展示当前任务及其审计结果，不伪造后端尚未支持的 AgentRun 历史列表。
- 工作区写入 URL 查询参数 `workspace=agent`；Chat 默认值不强制写入 URL。
- 当前 AgentRun 写入 `run=<uuid>`，使刷新或切换工作区后可以重新查询运行记录。
- 切换工作区保留现有 `conversation` 查询参数，返回 Chat 时仍可恢复原会话。

本批不引入 React Router。小型 URL helper 负责读取、校验和更新 `workspace`、
`run` 参数，并保留其他 query 与 hash。无效 `run` 不是可查询身份，按无当前 Run
处理，不向后端发送无效 UUID。

## 3. Component Boundaries

### 3.1 Application and Sidebar

`App` 读取当前 workspace，并在 `ChatPage` 与 `AgentPage` 之间切换。两个页面通过
回调更新 URL；当前实现与 conversation URL 逻辑一致，使用 `history.replaceState`
而不创建新的浏览器历史栈，不新增 `popstate` 路由器或跨页面业务状态机。

`WorkspaceSidebar` 增加工作区导航，并使用可辨识 props 保持边界：

- Chat 模式继续接收会话、New Chat 和选择会话回调。
- Agent 模式只展示工作区导航、Agent 说明和 API health，不显示不可用的运行历史。
- 两种模式都保留后端连接状态和可追踪的 API base URL。

### 3.2 AgentPage

`AgentPage` 负责 orchestration：

1. 独立加载 API health 与模型列表。
2. 只保留 `supports_tools=true` 的模型。
3. 如果 URL 包含有效 Run UUID，并行读取 AgentRun 与 ToolCalls。
4. 接收任务输入并调用同步 Agent POST。
5. 将成功返回的 Run ID 写回 URL。
6. 把运行、传输错误和页面状态交给展示组件。

状态明确区分：

- `loading`：模型或历史 Run 正在读取，或任务正在执行。
- `empty`：页面可用但尚未运行任务。
- `no-models`：没有 `supports_tools=true` 的模型，任务提交被禁用。
- `model-error`：模型列表加载失败，任务提交被禁用，但已恢复的 Run 仍可阅读。
- `error`：Run 查询或提交发生 HTTP、网络或响应读取失败，显示安全消息和可用的
  Request ID。
- `result`：展示 `completed` 或结构化 `failed` AgentRun。

同步 POST 返回 HTTP 201 且 `status="failed"` 时，这是已持久化、可审计的运行结果，
不是 transport error。页面必须显示 Run ID、状态和 `error`，不能把它折叠成普通
错误横幅。

### 3.3 AgentTaskForm

`AgentTaskForm` 只负责：

- 工具模型选择；候选已由页面过滤。
- 非空任务输入。
- 提交状态与禁用规则。
- `New task`，清空当前运行和 `run` URL 参数。

请求发送选定的 `provider`、`model` 与 trim 后的 `input`。`temperature`、
`max_tokens` 和 `max_steps` 使用后端默认值，本批不增加高级设置面板。

### 3.4 AgentRunPanel

`AgentRunPanel` 是所有运行状态的统一展示入口。结果状态展示：

- AgentRun status、Run ID、Conversation ID、开始时间与耗时。
- completed 的 final answer。
- structured failed 的安全错误。
- `ToolCallTimeline`。

Run ID、Conversation ID、ToolCall database ID 和 Provider `tool_call_id` 保持可见、
可复制且不改写，以满足工程工作台的追踪要求。

### 3.5 ToolCallTimeline and ToolCallCard

`ToolCallTimeline` 按 API 返回顺序渲染 ToolCall。空数组显示“本次运行未调用工具”，
但不暗示调用失败。数据库尚无严格 sequence 字段，因此恢复查询的
`created_at, id` 顺序只描述为确定性展示顺序。

`ToolCallCard` 展示：

- Tool 名称与状态。
- Provider `tool_call_id` 和 database ID。
- 参数的稳定 JSON 展示。
- latency；未知值显示明确占位，不伪造 `0 ms`。
- result content/data/metadata 的有界摘要。
- ToolCall `error` 或失败 `ToolResult.error`。

状态颜色映射：

- `pending`、`running`：中性/进行中。
- `success`：成功。
- `failed`、`timeout`、`blocked`：错误/受阻。

结果摘要在 UI 层限制长度，避免大 Tool 结果占满页面；完整响应仍由 API 保持，
本批不改变后端持久化或响应契约。格式化 helper 只处理已解析 JSON，不执行 HTML，
React 默认转义所有文本。

## 4. TypeScript and API Contracts

新增 `frontend/src/types/agent.ts`，精确镜像后端 JSON：

- `AgentRunStatus`
- `ToolCallStatus`
- `ToolResult`
- `AgentRunCreate`
- `AgentRun`
- `ToolCall`
- `AgentRunExecution`

时间字段保持 ISO string，UUID 保持 string；前端不假装进行运行时 schema 校验。
字段名使用公开 API 语义：`input`、`arguments`、`result`、`error`，不引入 ORM 的
`arguments_json`、`result_json` 或 `error_message`。

新增 `frontend/src/api/agent.ts`：

```text
createAgentRun(request)           -> AgentRunExecution
fetchAgentRun(runId)              -> AgentRun
fetchAgentToolCalls(runId)        -> ToolCall[]
```

请求都使用复数 `/agents/runs`，不访问不存在的单数 alias。POST 发送 JSON
`Content-Type`。错误解析保留统一 envelope 中的：

- HTTP status
- `error.code`
- `error.message`
- `error.request_id`

Agent API 使用专用 `AgentApiError` 承载这些字段；UI 不展示响应原文、Provider
诊断、堆栈、SQL 或绝对路径。非 JSON/网络失败使用固定 fallback，且没有 Request ID
时不显示伪造 ID。

## 5. Data Flow

### 5.1 Enter Agent Workspace

```text
App reads workspace
  -> AgentPage loads health + models
  -> filter supports_tools=true
  -> valid run query?
       no  -> empty task state
       yes -> GET AgentRun + GET ToolCalls in parallel
             -> AgentRunPanel result or safe error
```

模型列表为空与模型请求失败是不同状态。前者说明当前 Registry 没有工具模型，后者
说明当前不能提交新任务。模型、health 与 Run 查询互不作为对方的前置条件；即使模型
Registry 或 Provider 配置不可用，URL 指向的已持久化 Run 仍应通过两个 GET 接口恢复
和展示。

### 5.2 Submit Task

```text
trim input
  -> disable duplicate submit
  -> POST AgentRun
  -> completed: show final answer + ToolCalls
  -> structured failed: show audited failed result + ToolCalls
  -> HTTP/network error: show safe error + Request ID when available
  -> write run UUID only after a 201 AgentRun response
```

页面在同步请求期间显示 loading，且不提供取消按钮，因为后端没有可持久化的取消
契约。再次运行以新结果替换当前面板；`New task` 清空结果但保留选定模型。

## 6. Quiet Workspace Visual Design

界面延续现有灰白底、细边框、绿色成功与红色错误语义，不创建营销式 hero、渐变或
大面积装饰。桌面布局保持侧栏 + 主工作区；Agent 主区使用有界内容宽度，按任务表单、
运行摘要、final answer、ToolCall 时间线从上到下扫描。

移动端沿用现有单列 shell。工作区切换、模型选择、任务输入、Run IDs 和 ToolCall
JSON 不得横向撑破视口；长 ID 和 JSON 允许换行。交互控件保留可见 focus 状态，
loading 与状态变化使用文本/ARIA，而不只依赖颜色。

## 7. Testing Strategy

实现严格按 RED -> GREEN：

1. URL helper 测试 workspace/run 的读取、UUID 拒绝、更新与 query/hash 保留。
2. Agent API 测试 POST path/body、GET run、GET ToolCalls、201 structured failed、
   envelope 错误与 Request ID、非 JSON fallback。
3. ToolCall helper/组件测试 `pending`、`running`、`success`、`failed`、`timeout`、
   `blocked`、未知 latency、有界摘要与安全文本渲染。
4. Timeline 测试空 ToolCalls 与顺序保持。
5. AgentRunPanel 测试 loading、empty、no-models、transport error、completed、
   structured failed，并断言 Run/Conversation/ToolCall IDs 可见。
6. Agent 页面测试只选择 tools-capable 模型、提交禁用和当前 Run 恢复的纯逻辑边界。
7. Chat 页面回归测试默认 workspace、会话 UI 和现有初始化状态不被破坏。

完整 Gate：

- Frontend `npm run typecheck`、完整 Vitest、production build。
- Backend 完整 pytest 与 `pip check`，证明纯前端改动没有破坏 API 基线。
- 使用完全 mock 的 health、models 和 Agent API 做浏览器 smoke：进入 Agent、提交
  “读取 README 并总结项目结构”、看到 `read_file` ToolCall、参数、成功状态、耗时、
  摘要、final answer 与 IDs。
- 浏览器检查桌面与移动宽度、Chat 回归，以及 no-models、loading、HTTP error、
  structured failed、completed 关键状态；不调用真实 Provider 或网络 Tool。

本批记录浏览器验证证据，但正式封版截图仍属于 `P2-M5-S6`，不提前完成。

## 8. Documentation and Review Gate

实现完成后同步：

- README / README_CN：Agent 工作区入口、tools-capable model 前提和 mock 验收边界。
- CHANGELOG：记录 AgentRun 与 ToolCall 前端展示。
- `docs/12-agent-api.md`：移除“尚无前端”的陈旧限制，增加 UI 使用与仍保留限制。
- `docs/00-project-overview.md`、`docs/01-architecture.md`：阶段更新到 M4 S6。
- Plan 2 执行步骤表：只标记 Batch 11 与 S4～S6，记录实际测试和浏览器证据。

Codex self-review 检查：

- diff 只覆盖 S4～S6 与必要文档。
- 没有后端 schema、数据库、Provider、Tool 安全或后续 Plan runtime 改动。
- 没有真实 secret、真实 Provider 调用、未跟踪敏感截图或生成物。
- Chat/Streaming/会话历史保持回归通过。
- loading、empty/no-models、error、completed/failed 均有证据。
- 无阻塞项后，M4 才可标记完成；下一批只能进入 `P2-M5-S1～S3`。

不使用 Claude Code、Fable 5 或子代理。用户在验证与 Codex self-review 完成后手动
创建 commit。
