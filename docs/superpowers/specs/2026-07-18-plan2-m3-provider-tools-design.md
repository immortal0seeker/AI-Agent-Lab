# Plan 2 M3 Provider Tools Design

## 1. Scope

本设计只覆盖 `P2-M3-S1～S3`：

- 扩展 `BaseLLMProvider` 的非流式 Chat 契约，使请求可携带函数 Tool 定义；
- 扩展 `OpenAICompatibleProvider`，发送 Chat Completions `tools` 并解析非流式 `tool_calls`；
- 新增 Tool Registry 到 LLM Provider Tool 定义的强类型适配器；
- 使用 Mock Provider、`httpx.MockTransport` 和临时目录验证，不调用真实或付费 Provider。

本批不实现 Agent Loop、Tool 执行、Tool observation 回填、AgentRun/ToolCall service、Agent API、前端、流式 Tool Call 聚合或任何后续 Plan 能力。

## 2. Chosen Architecture

采用“强类型 Provider 契约 + 独立 Tool Schema Adapter”。Tool 核心继续只负责可执行 Tool、Registry 和 JSON Schema；Provider 层拥有模型请求/响应 DTO；适配器是两层之间唯一的转换点。业务层和后续 Agent Loop 不接触 OpenAI 原始响应，也不解析 `function.arguments` 字符串。

未采用以下方案：

- 原始 `dict` 透传：实现短，但会把字段拼写、JSON 解析和错误语义分散到调用方；
- 直接复用 `app.schemas.tool.ToolCallRequest`：会让 Provider 层依赖 API/持久化传输 schema，边界方向错误。

## 3. Provider Contract

`backend/app/providers/llm/base.py` 新增两类强类型值：

- `LLMToolDefinition`：OpenAI-compatible 函数定义，包含固定 `type="function"`、函数名、描述和 object 根 JSON Schema；
- `LLMToolCall`：Provider 中立的已解析调用，包含 `tool_call_id`、`tool_name` 和 `arguments: dict[str, Any]`。

`ChatRequest` 增加 `tools: tuple[LLMToolDefinition, ...] = ()`。空元组表示普通 Chat，Provider payload 必须省略 `tools`，以保持 Plan 1 行为和请求快照不变。

`LLMResponse` 调整为：

- `content: str | None`；
- `tool_calls: tuple[LLMToolCall, ...] = ()`；
- `content` 非 `None` 或 `tool_calls` 非空至少满足一项。

这样可以表达官方 Chat Completions 中“助手发起 Tool Call 时 content 可以缺失”的响应，同时保持普通文本响应不变。一次响应允许按 Provider 原顺序携带多个 Tool Call。

`ChatChunk` 和文本流式契约本批不扩展。若 `stream_chat()` 收到非空 `tools`，`OpenAICompatibleProvider` 必须在发起 HTTP 请求前抛出固定、可测试的 `ProviderUnsupportedFeatureError`，避免静默丢失分片式 Tool Call。流式聚合必须由未来明确 Step 单独设计和测试。

## 4. Tool Schema Adapter

新增 `backend/app/providers/llm/tool_adapter.py`，提供：

```python
def build_llm_tool_definitions(
    registry: ToolRegistry,
) -> tuple[LLMToolDefinition, ...]:
    ...
```

适配器按 Registry 注册顺序读取 Tool，并复制以下字段：

- `name`；
- `description`；
- `parameters_schema`。

它不调用 Tool、不读取工作区文件、不修改 Registry，也不依赖内置 Tool 的具体类型。返回定义与 Registry 内部 schema 相互独立；调用方修改序列化结果不能导致注册定义漂移。

函数名继续遵守最多 64 个 ASCII 字母、数字、下划线或连字符的既有边界。参数 schema 必须 JSON 可序列化且根为 object。适配器不设置 `strict=true`，因为现有 Draft 2020-12 schema 未承诺只使用 OpenAI strict mode 支持的 JSON Schema 子集。

## 5. OpenAI-Compatible Mapping

非流式请求映射：

```text
ChatRequest.tools
-> payload.tools[]
-> {"type": "function", "function": {"name", "description", "parameters"}}
```

非流式响应映射：

```text
choices[0].message.tool_calls[]
-> 校验 type == "function"
-> 校验 id / function.name
-> json.loads(function.arguments)
-> 校验 arguments 是 object
-> LLMToolCall
```

解析必须保留 Tool Call 顺序，并拒绝重复 `tool_call_id`。以下情况统一转换为固定消息的 `ProviderResponseError`，不得回显原始 arguments、上游正文、凭据或异常文本：

- `tool_calls` 不是非空数组；
- 调用类型不是 `function`；
- ID 或函数名缺失、为空或超出契约；
- arguments 不是字符串、不是合法 JSON，或 JSON 根不是 object；
- Tool Call ID 重复；
- content 缺失且没有有效 Tool Call。

普通未携带 tools 的请求若意外收到 Tool Call，也视为无效 Provider 响应，防止 Plan 1 Chat 路径进入尚未实现的 Agent 行为。

## 6. Model Capability Boundary

`backend/app/providers/llm/models.json` 中的示例模型继续保持 `supports_tools=false`。本批证明适配器支持协议格式，不证明任意真实模型具备 Tool Calling 能力，也不调用真实 Provider。

后续 `P2-M3-S4～S6` 的 Agent service 必须在调用前根据 `ModelRegistry` 检查所选模型的 `supports_tools`，并对不支持的模型返回明确错误。本批不提前实现该 service 或修改示例模型能力声明。

## 7. Error Handling

- 请求 DTO 或 Tool Definition 构造错误由 Pydantic 在本地拒绝；
- 流式 tools 请求使用 `ProviderUnsupportedFeatureError`，且不能产生网络请求；
- 上游成功响应中的 Tool Call 结构或 arguments 错误使用安全的 `ProviderResponseError`；
- HTTP 状态、超时、传输错误继续使用 Plan 1 的既有分类；
- 原始 Tool arguments 只存在于进程内解析输入，不写日志、不写数据库、不进入异常文本。

## 8. Test Strategy

严格按 TDD 分三组推进：

1. Provider contract：先写失败测试，覆盖 tools 强类型字段、普通请求默认值、Tool Call 响应、content/tool_calls 一致性和 Mock Provider 接收 tools；
2. Schema adapter：先写失败测试，覆盖 `read_file`/`list_dir` 顺序、完整序列化、空 Registry 和防御性复制；
3. OpenAI-compatible adapter：先写失败测试，覆盖请求 payload、content 为 null 的单/多 Tool Call、finish reason/usage、非法 JSON、非 object、错误类型、重复 ID、未请求 Tool Call 和流式明确拒绝。

每组完成 RED、GREEN、聚焦回归后，再运行：

- Provider 与 Tool 聚焦测试；
- Backend 全量 pytest 与 `pip check`；
- Frontend typecheck、完整 Vitest 和 production build；
- 无真实 Provider 的 FastAPI health/OpenAPI/request-id smoke；
- Markdown 链接、secret、生成物、Plan 边界、`git diff --check` 和 `git status` 检查。

## 9. Documentation

实现后同步：

- `docs/03-llm-provider.md`：从“Tool Calling 缺失”更新为非流式协议支持及流式限制；
- `docs/10-tool-calling-design.md`：记录 Registry -> Provider adapter 和当前数据流；
- `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`：补充 S1～S3 的真实 TDD 与验收证据；
- README、README_CN、`docs/00-project-overview.md`、`docs/01-architecture.md`：仅在其中的当前阶段或下一批描述已过时时做最小同步。

本批不更新 `CHANGELOG.md`，因为尚未形成用户可执行的 Agent 闭环，也不创建版本 tag。

## 10. Acceptance Gate

本批完成必须同时满足：

- Mock Provider 能接收强类型 tools；
- OpenAI-compatible 非流式请求能发送 `read_file` 和 `list_dir` schemas；
- 合法单个和多个 Tool Call 能解析为 Provider 中立对象；
- 无效 Tool Call 响应失败安全且不泄漏原始值；
- 普通 Chat/Streaming、Provider 错误分类和 Plan 1 API 回归不受影响；
- 流式 tools 明确拒绝且不触发 HTTP；
- 未更改数据库、未执行 Tool、未实现 Agent Loop、未调用真实 Provider；
- Codex self-review 和新鲜全量验证无阻塞项。
