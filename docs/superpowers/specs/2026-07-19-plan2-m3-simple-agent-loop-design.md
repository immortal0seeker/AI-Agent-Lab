# Plan 2 M3 Simple Agent Loop Design

## 1. Scope

本设计只覆盖 `P2-M3-S4～S6`：

- `S4`：建立 Simple Agent Loop 基础流程；无需工具的任务直接返回模型文本。
- `S5`：支持模型选择 Tool、顺序执行 Tool、回填 assistant Tool Call 与 Tool observation，再生成最终答案。
- `S6`：把每次执行写入现有 `agent_runs` 与 `tool_calls`，并保存用户消息和最终助手消息。

本批不实现 Agent API、前端、流式 Tool Calling、通用 `max_steps`、Tool 超时、重试、取消、并行执行或完整失败恢复策略。上述循环控制与失败策略属于 `P2-M3-S7`；Agent API 与前端属于后续 Milestone。也不实现 RAG、Embedding、Memory、MCP、Shell Tool、`write_file`、`delete_file` 或任何未来 Plan 能力。

## 2. Chosen Architecture

采用“Provider 中立消息协议 + 服务化单轮闭环 + 现有 ORM 持久化”。

- `backend/app/providers/llm/base.py` 只表达模型可理解的文本消息、assistant Tool Call 消息和 Tool observation 消息。
- `backend/app/providers/llm/openai_compatible.py` 独占 Chat Completions wire format 的序列化。
- `backend/app/agents/simple_agent.py` 负责编排模型、Registry、Tool 与持久化，不接触 OpenAI 原始字典。
- `ConversationService` 继续负责 Conversation 与 Message；Agent service 只在同一 SQLAlchemy 事务中 `flush`，不自行 `commit`。
- 现有 `AgentRun`、`ToolCall`、状态与迁移已经满足本批，不新增字段、状态或 migration。

未采用以下方案：

- 在 Agent 层直接拼 OpenAI `dict`：会把 Provider 字段和 JSON 编码泄漏到业务层。
- 当前建立通用 runtime/event engine：属于 Plan 5 Agent Runtime v2，超出本批边界。
- 当前引入通用多步循环：会提前实现 `P2-M3-S7` 的 `max_steps` 与失败返回策略。

## 3. Provider-Neutral Observation Contract

现有 `ChatMessage(role, content)` 需要扩展，才能表达官方 Chat Completions Tool observation 协议。继续使用一个强校验 DTO，避免改动普通 Chat 调用方：

```python
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: tuple[LLMToolCall, ...] = ()
    tool_call_id: LLMToolCallIdentifier | None = None
```

模型校验规则：

- `system` / `user`：必须有字符串 `content`，不得带 `tool_calls` 或 `tool_call_id`。
- 普通 `assistant`：必须有字符串 `content`，不得带 `tool_call_id`。
- 发起 Tool Call 的 `assistant`：允许 `content=None`，必须带非空且 ID 唯一的 `tool_calls`，不得带 `tool_call_id`。
- `tool`：必须有字符串 `content` 和非空 `tool_call_id`，不得带 `tool_calls`。

`ChatRequest.messages` 继续使用 `list[ChatMessage]`，因此 Plan 1 普通 Chat 和 Streaming 源码保持兼容。普通消息序列化结果仍只有 `role` 与 `content`。

OpenAI-compatible adapter 新增显式 `_serialize_message()`：

- 普通消息映射为 `{"role", "content"}`。
- assistant Tool Call 映射为 `role="assistant"`、可选 `content` 和 `tool_calls[]`；每项包含 `id`、固定 `type="function"`、`function.name` 与确定性 JSON 字符串 `function.arguments`。
- Tool observation 映射为 `role="tool"`、`content` 与对应 `tool_call_id`。

arguments 序列化使用 `ensure_ascii=False`、紧凑 separators 和 `allow_nan=False`。Provider wire format 只能存在于 adapter 内。

`LLMToolCall.arguments` 本身也必须在 DTO 构造时完成标准 JSON 可序列化校验并拒绝 NaN/Infinity。真实 adapter 已在解析阶段保证这一点；这里补强 Mock Provider 和未来其他 Provider adapter 的统一契约，避免非法参数推迟到 observation wire 序列化时才失败。

## 4. Agent Service Contract

新增 `backend/app/agents/`，只包含当前 Milestone 已到达的 Simple Agent 能力：

- `__init__.py`
- `errors.py`
- `simple_agent.py`

`SimpleAgentRequest` 是服务层 frozen Pydantic DTO，使用 `extra="forbid"`，并在任何数据库写入前校验非空 content/provider/model、temperature 范围和正数 max_tokens。字段与当前非流式 Chat 基本一致：

- `content: str`
- `provider: str`
- `model: str`
- `conversation_id: UUID | None = None`
- `temperature: float = 0.7`
- `max_tokens: int | None = None`

`SimpleAgentResult` 是服务层不可变 dataclass，返回：

- `conversation`
- `user_message`
- `assistant_message`
- `agent_run`
- `tool_calls`（按执行顺序）
- `provider`
- `model`
- 两次 Provider 响应的 usage 不在本批持久化，也不引入新的聚合 DTO；此限制在文档中记录。

`SimpleAgentService` 构造依赖：

- SQLAlchemy `Session`
- `ModelRegistry`
- `Mapping[str, BaseLLMProvider]`
- `ToolRegistry`

服务首先校验模型存在、`supports_tools=true`、Provider 可用，然后才创建持久化对象。这样配置错误不会留下半成品运行记录。

## 5. Single Tool-Round Flow

用户已确认本批采用单轮工具闭环：

```text
goal
  -> conversation + user Message
  -> AgentRun(running, started_at)
  -> provider.chat(history + tools)
       -> text only: complete run
       -> one or more Tool Calls:
            AgentRun(waiting_tool)
            -> validate + execute each call in response order
            -> persist each ToolCall terminal result
            -> append assistant Tool Call message
            -> append one Tool observation per call
            -> AgentRun(running)
            -> provider.chat(enriched messages + same tools)
                 -> final text: complete run
                 -> more Tool Calls: stable AgentLoopIncompleteError
```

首轮若同时包含 `content` 与 `tool_calls`，Tool Calls 优先；可选 content 作为 assistant Tool Call 消息的一部分回填，不作为最终答案。第二轮必须提供非空最终文本且不得继续请求 Tool。

本批最多两次 Provider 调用。`P2-M3-S7` 再把它泛化为默认三步的 `max_steps` 循环，并补齐超时和全面失败返回策略。

## 6. Tool Execution and Observation

每个 `LLMToolCall` 按 Provider 返回顺序执行：

1. 立即创建并 `flush` 一条 `ToolCall(status="running")`，保存 defensive-copy 后的 arguments。
2. 用 `ToolRegistry.get_tool()` 定位 Tool。
3. 在 Agent 边界调用 `validate_tool_arguments()`，保证所有 Tool 都遵守统一 JSON Schema 校验，而不依赖内置 Tool 自己是否重复校验。
4. 把校验函数返回的防御性副本传给 `await tool.run(validated_arguments)`；不得让 Tool 修改 ORM 中已记录的原始 arguments。
5. 把完整 `ToolResult.model_dump(mode="json")` 写入 `result_json`。
6. 以同一 JSON 对象的确定性紧凑 JSON 字符串作为 Tool observation `content`。

终态映射：

- `ToolResult.success=true` -> `ToolCall.status="success"`，`error_message=None`。
- 参数错误、未知 Tool、Tool 返回失败、Tool 返回不匹配的 `tool_name`、ToolResult 含非标准 JSON 值或 Tool 抛出异常 -> 安全失败 `ToolResult`，`ToolCall.status="failed"`。

固定安全错误语义：

- 未知 Tool：`Tool is not available`
- 参数校验失败：使用现有稳定、已脱敏的 `ToolArgumentValidationError` 消息
- 未预期执行异常：`Tool execution failed`

不得把原始异常、工作区绝对路径、Provider 原始正文、凭据或敏感文件内容写入 `error_message`、日志或异常文本。失败 Tool observation 仍回填模型，使模型有机会在第二轮给出可读最终答案。Tool 超时专属状态属于 S7，本批不使用。

## 7. Persistence and State Semantics

本批只使用已有状态，不修改状态机定义：

### AgentRun

- 创建：`status="running"`、`goal`、`conversation_id`、`user_message_id`、`started_at`。
- 首轮请求 Tool：`status="waiting_tool"`。
- Tool observation 全部生成后：恢复 `status="running"`。
- 成功：`status="completed"`、`final_answer`、`ended_at`、`latency_ms`。
- 第二轮仍请求 Tool 或缺少最终文本：`status="failed"`、固定 `error_message`、`ended_at`、`latency_ms`，然后抛出稳定 Agent domain error。

### ToolCall

- 创建并执行：`status="running"`、`started_at`。
- 结束：`status="success"` 或 `"failed"`、`result_json`、安全 `error_message`、`ended_at`、`latency_ms`。
- `tool_call_id`、`tool_name`、`arguments_json`、`agent_run_id` 与 `conversation_id` 全部来自 Provider DTO 和当前运行上下文。

### Messages

- 保存用户输入和最终 assistant 文本。
- 不把中间 assistant Tool Call / Tool observation 写入现有 `messages` 表，因为其 `role/content` 结构无法无损表达调用关联；完整调用输入和结果保存在 `ToolCall`，协议消息只在本次运行内构造。
- 成功后调用 `ConversationService.record_successful_turn()`；失败不更新成功回合元数据。

服务不 `commit`。未来 API 的数据库依赖负责提交；调用方异常时的 transaction policy 将在 S7/API 集成时统一完成。测试必须显式 commit 后重新查询，证明正常路径记录可持久化。

本批不新增 `LLMCall`：当前模型没有 `agent_run_id` 关联，强行写入会产生无法归属的观测记录或要求 migration。Provider 调用级 cost/usage 持久化作为后续可观测性桥接项记录，不提前改库。

现有 `tool_calls` 没有显式 sequence 字段，本批 S5 的运行时和 `SimpleAgentResult.tool_calls` 必须保持 Provider 顺序，但 S6 只承诺每次调用都有可查询记录，不宣称数据库关系本身可还原并列调用的严格顺序。跨运行的严格步骤时间线由后续计划中的 `agent_step` / Trace 设计统一解决；本批不为该未来结构修改已经验收的 M1 migration。

## 8. Error Boundary

新增 Agent domain errors，消息固定且不含敏感输入：

- `AgentError`
- `AgentModelNotFoundError`
- `AgentModelToolsUnsupportedError`
- `AgentProviderUnavailableError`
- `AgentLoopIncompleteError`：第二轮继续请求 Tool，或任一终止响应没有非空最终文本。

Tool 层的预期失败被转换为 Tool observation，不使整个运行崩溃。Provider 请求异常仍保持原有 `LLMProviderError` 分类；S7 才设计全面的 Agent 失败返回和重试规则。本批若 Provider 异常向上传播，调用方事务回滚，不能声称已持久化失败运行。

## 9. TDD Strategy

按以下 RED -> GREEN 顺序执行：

1. Provider observation contract：
   - 普通消息完全兼容；
   - assistant Tool Call 与 Tool observation 的合法/非法组合；
   - OpenAI-compatible 两种消息的精确 payload；
   - 多个 Tool Call arguments 的确定性编码和顺序。
2. `S4` 无 Tool 路径：
   - Mock Provider 收到 Registry 定义；
   - 直接文本只调用 Provider 一次；
   - 创建 Conversation、用户/助手 Message 和 completed AgentRun；
   - 不创建 ToolCall。
3. `S5` Tool 闭环：
   - 固定 Mock 首轮请求 `read_file`，第二轮返回最终答案；
   - 精确验证 assistant Tool Call + Tool observation 回填；
   - 多 Tool Call 顺序；
   - 未知 Tool、参数失败、ToolResult 失败、执行异常均安全回填；
   - 第二轮再次请求 Tool 稳定失败，不进入第三次调用。
4. `S6` 持久化：
   - commit 后全新查询 AgentRun/ToolCall；
   - FK、顺序、状态、arguments/result、时间戳与 latency；
   - failed ToolCall 仍保留安全结果；
   - 无需 migration。

所有测试使用 Mock Provider、临时 SQLite 和临时工作区目录；不得调用真实 Provider、付费 API、网络 Tool、真实 `.env` 或用户数据库。

## 10. Documentation and Acceptance

实现后最少同步：

- `docs/10-tool-calling-design.md`：当前单轮闭环、消息回填、持久化与 S7 限制。
- `docs/03-llm-provider.md`：Provider 中立 observation DTO 与 OpenAI-compatible mapping。
- `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`：S4～S6 实际文件与验证证据。
- README、README_CN、项目 overview/architecture：仅在现有“当前状态/下一批”文字过时时做最小同步。
- `CHANGELOG.md`：Simple Agent Loop 已形成可执行后端能力，应记录未发布变更，但不得声称已有 API/UI。

完成 Gate：

- 无 Tool 任务一次 Provider 调用完成。
- Tool 任务正确发送工具定义、执行一个或多个调用、按 ID 回填 observation，并在第二次 Provider 调用获得最终答案。
- 每个正常执行都能持久化 AgentRun；每个 Tool Call 都有完整、安全、可查询的数据库记录。
- 第二轮继续请求 Tool 时不会无限循环。
- 普通 Chat/Streaming 与 P2-M3-S1～S3 回归不受影响。
- Backend 全量 pytest、`pip check`、Frontend typecheck/Vitest/build、FastAPI health/OpenAPI/request-id smoke 全部新鲜通过。
- 没有真实 Provider/网络调用、数据库 migration、秘密泄漏、跨 Plan 实现或未记录限制。
- Codex self-review 无阻塞问题；不使用 Claude Code，Fable 5 仅在 6 个 Plan 全部完成后由用户决定。
