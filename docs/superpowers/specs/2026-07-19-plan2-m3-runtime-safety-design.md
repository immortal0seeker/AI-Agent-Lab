# Plan 2 M3 Agent Loop Runtime Safety Design

## 1. Scope

本设计只覆盖 `P2-M3-S7～S8`：

- `S7`：把现有单轮 Tool 闭环泛化为有界多步循环，执行 Tool 超时控制，提供可持久化的失败结果，并建立 Tool observation 压缩雏形。
- `S8`：完成 M3 Codex self-review，新增 `docs/11-simple-agent-loop.md`，同步当前状态、限制和验证证据。

本批不实现 Agent API、前端、流式 Tool Calling、自动重试、用户取消接口、并行 Tool 执行、Provider 调用级 `LLMCall` 关联、显式 ToolCall sequence、复杂 Runtime、Planner、Human Approval、RAG、Embedding、Memory、MCP、Shell Tool 或文件写入/删除工具。Agent API 与前端属于 M4；通用 Runtime Policy、重试和审批属于后续 Plan。

## 2. Chosen Architecture

保留现有 `SimpleAgentService` 的服务边界，采用“请求级步数策略 + 循环内顺序 Tool 执行 + 结构化终态结果”：

- `SimpleAgentRequest.max_steps` 表达一次运行允许的 Provider 决策次数。
- `SimpleAgentService` 在同一方法内循环调用 Provider、执行 Tool 并追加 observation，不建立 Plan 5 的 Runtime/Event Engine。
- Tool 自身的 `timeout_seconds` 是每次调用的超时来源；Agent 层负责执行超时并记录 `timeout` 终态。
- 运行创建后的可预期终止失败不再依赖异常交付，而是返回包含 failed `AgentRun` 的 `SimpleAgentResult`。
- ToolResult 的数据库记录保持完整；只有发送给 Provider 的 observation 在超限时生成压缩副本。
- 服务继续只 `flush`、不 `commit`，由 M4 API 或其他调用方统一提交事务。

未选择继续抛出所有运行时异常，因为常见 API 事务依赖会在异常路径回滚，导致已经构造的失败 AgentRun 无法作为可查询结果交付。也不引入成功/失败联合 DTO，避免在当前简单服务和后续 M4 schema 之间增加不必要的分支类型。

## 3. Step Counting

`SimpleAgentRequest` 新增：

```python
max_steps: int = Field(default=3, ge=1, le=10)
```

一个 step 定义为一次 Provider `chat()` 决策，而不是单个 Tool Call：

- 同一 Provider 响应中的多个 Tool Call 仍只消耗一个 step。
- 文本终态也消耗一个 step。
- 默认 `max_steps=3` 最多允许两轮 Tool 决策和第三轮最终文本。
- `max_steps=1` 只允许模型直接回答；若唯一响应要求 Tool，则不执行该 Tool，运行以最大步数失败。
- 当第 `max_steps` 个响应仍包含 Tool Call 时，不执行这些调用、不创建对应 ToolCall 行，也不进行额外 Provider 调用。
- Tool Call ID 必须在一次 AgentRun 的所有已执行轮次中唯一；后续响应复用已执行 ID 时，在 Tool 执行和数据库写入前以安全 Provider 失败终止。

最大步数固定错误为：

```text
Agent reached the maximum number of steps
```

这一语义保证步数上限同时约束 Provider 调用次数和 Tool 副作用边界。Plan 2 的 Tool 全部只读，但该规则也为未来有副作用工具保留安全默认值。

## 4. Multi-Step Message Flow

运行从已持久化的 Conversation history 与当前用户消息开始：

```text
for step in 1..max_steps:
    provider.chat(messages + tools)
        -> final text: complete
        -> Tool Calls and step == max_steps: fail without execution
        -> Tool Calls and capacity remains:
             AgentRun(waiting_tool)
             execute calls sequentially
             persist terminal ToolCalls
             append assistant Tool Call message
             append correlated Tool observations
             AgentRun(running)
             continue
```

每轮保留 Provider 返回的 Tool Call 顺序。每个 assistant Tool Call 消息后紧跟该轮所有 observation，再进入下一次 Provider 请求。所有轮次使用同一组防御性构造的 Tool definitions。

最终文本必须非空。空白终态使用既有固定错误：

```text
Agent did not produce a final answer
```

## 5. Tool Timeout

Agent 在 Registry lookup 和参数校验成功后，使用 Tool 的 `timeout_seconds` 包裹 `tool.run()`：

- 在期限内返回：沿用 `success` / `failed` 映射。
- 超时：取消等待中的协程，生成固定安全 ToolResult，记录 `ToolCall.status="timeout"`。
- 固定错误：`Tool execution timed out`。
- 超时 observation 仍回填 Provider；AgentRun 返回 `running` 并继续下一步，让模型有机会解释失败或改用其他只读 Tool。
- 同轮其余 Tool Call 继续按顺序执行；一个 Tool 超时不跳过其他调用。

Python 异步取消是协作式的。若 Tool 内部把阻塞工作转交线程，超时不能强制终止已经运行的底层线程；因此 Tool 实现仍必须保持有界 I/O。该限制写入正式文档，不在 Plan 2 引入进程隔离。

自动 retry 不属于本批。重试可能重复未来的有副作用操作，也不能绕过权限或审批；在 Human Approval 和正式 Runtime Policy 出现前维持零自动重试。

## 6. Structured Failure Return

`SimpleAgentResult.assistant_message` 改为 `Message | None`。成功仍返回 assistant Message；运行失败返回：

- `assistant_message=None`
- `agent_run.status="failed"`
- `agent_run.final_answer=None`
- 固定、可读、脱敏的 `agent_run.error_message`
- 已终止的 ToolCall 记录与执行顺序结果
- Conversation 和用户 Message，供 M4 API 提交并查询

以下前置错误发生在任何持久化之前，继续抛出既有 Agent domain error：

- 模型不存在
- 模型不支持 tools
- Provider 未配置
- Conversation 不存在或请求 DTO 非法

以下错误发生在 AgentRun 创建后，转换为结构化失败结果：

| 场景 | AgentRun 错误 |
|---|---|
| 达到最大步数仍请求 Tool | `Agent reached the maximum number of steps` |
| Provider timeout | `Model request timed out` |
| 其他 Provider/意外执行异常 | `Model request failed` |
| Provider 返回空白终态 | `Agent did not produce a final answer` |

只捕获 Provider 调用边界内的普通异常；`asyncio.CancelledError` 等取消信号不被吞掉。数据库 `flush`、Message 持久化和约束异常也不转成业务失败结果，仍交给调用方回滚，避免在失效事务中伪造可持久化状态。

Tool lookup、参数、返回失败、Tool 异常和 Tool timeout 仍属于 Tool observation，不直接失败整个 AgentRun。只有循环无法得到最终文本或 Provider 调用失败才终止 AgentRun。

## 7. Tool Observation Compression

增加 Agent 层 observation 字符上限：

```text
DEFAULT_MAX_TOOL_OBSERVATION_CHARS = 32_000
```

服务构造时可注入该值，最小允许值为 1,024。规则如下：

- 先对完整 ToolResult 生成标准、确定性 JSON。
- 未超过上限：保持现有 observation 完全不变。
- 超过上限：数据库 `result_json` 仍保存完整 ToolResult；Provider 只接收一个合法 JSON 压缩副本。
- 压缩副本保留 `tool_name`、`success`，将 `data` 置为 `null`，使用受限 metadata 标明 `observation_truncated=true` 和原始序列化字符数。`error` 最多保留 256 个字符，并按 JSON 转义后的实际预算继续缩短；超限时以单个省略号结尾。`content` 使用二分预算截断，直到整个 JSON 不超过上限。
- 压缩不得修改原 ToolResult、ORM `result_json` 或其他调用轮次。
- 即使固定字段自身无法在配置上限内表达，也必须返回合法、有界 JSON；构造参数的 1,024 字符下限、64 字符 Tool 名称上限与 256 字符压缩错误上限保证固定 envelope 可以表达。

该机制是字符级上下文保护，不是 token 精确计数或语义摘要。更智能的 Tool result summarization 属于后续可观测性/RAG 设计。

## 8. Persistence and State Semantics

本批复用现有 ORM 状态和 migration，不新增字段、约束或 revision：

### AgentRun

- Provider 决策前与 observation 回填后：`running`
- 执行一轮 Tool：`waiting_tool`
- 成功文本：`completed`
- 最大步数、Provider 失败或空白终态：`failed`

### ToolCall

- 创建：`running`
- ToolResult 成功：`success`
- 校验/ToolResult/Tool 异常：`failed`
- Tool 执行超时：`timeout`

最大步数终止时，最后一个尚未执行的 Provider Tool Call 不创建数据库行，因为系统没有尝试该调用。此前已执行的 ToolCall 保留。`SimpleAgentResult.tool_calls` 按所有轮次的实际执行顺序返回；数据库仍不宣称具有独立 sequence 字段。

运行失败时服务保持 Session 可提交且只调用 `flush`。M4 API 必须在收到结构化失败结果后正常提交，再把 AgentRun status/error 映射为响应；本批不实现该 API。

## 9. Testing Strategy

严格按 RED -> GREEN 覆盖：

1. `max_steps` DTO 校验、默认值与范围。
2. 两轮 Tool 后第三轮文本成功；每轮多个 Tool Call 仍只算一步。
3. 最后一步请求 Tool 时不执行、不创建新 ToolCall、不额外调用 Provider，并返回 failed result。
4. Tool 在期限内完成和 Tool timeout；timeout 状态、固定错误、后续 observation 与同轮后续 Tool 执行。
5. Provider timeout、Provider domain error、意外异常和空白终态都返回可提交的 failed AgentRun；前置错误仍无持久化并抛异常。
6. observation 未超限保持兼容；超限时 Provider JSON 有界且可解析，持久化 ToolResult 完整且未被修改。
7. 多步成功/失败在 SQLite commit、expire、reload 后状态一致。
8. Plan 1 Chat/Streaming、Provider tools、Tool 安全边界全部回归。

测试只使用 Mock Provider、受控异步 Tool、临时 SQLite 和临时目录。不得访问真实 Provider、网络、真实 `.env`、用户数据库或凭据。

## 10. S8 Documentation and Review Gate

新增 `docs/11-simple-agent-loop.md`，说明：

- 服务职责与调用流程
- Provider-neutral Tool observation
- `max_steps` 计数规则
- Tool timeout 与无自动 retry
- AgentRun / ToolCall 状态
- 结构化失败结果和事务所有权
- observation 压缩
- 当前无 API/UI/streaming Tool Calls/复杂 Runtime 的限制
- M4 接入契约

同步 README、README_CN、CHANGELOG、项目 overview/architecture、Provider/Tool Calling 文档和 Plan 2 执行步骤表中的过时状态。完成 Gate：

- Backend 全量 pytest 与 `pip check` 通过。
- Frontend typecheck、完整 Vitest 和 production build 通过。
- FastAPI health/OpenAPI/request-id smoke 不初始化真实 Provider。
- 全新临时 SQLite 上 Alembic `upgrade head`、`current --check-heads` 与 `alembic check` 通过；不触碰用户数据库。
- 文档本地链接、秘密模式、生成物、diff scope 与 `git diff --check` 通过。
- Codex self-review 对 S1～S8 的 Provider/Agent 边界、状态、失败语义与 Plan 边界无阻塞问题。
- 不使用 Claude Code 或 Fable 5，不开始 M4。
