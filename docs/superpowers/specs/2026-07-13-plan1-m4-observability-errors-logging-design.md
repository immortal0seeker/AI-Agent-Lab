# Plan 1 M4-S1～S3 Usage、错误与日志设计

## 1. 范围

本设计仅覆盖：

- `P1-M4-S1`：Token / Cost / Latency 记录
- `P1-M4-S2`：基础错误分类和统一 API 错误返回
- `P1-M4-S3`：基础日志

本批建立 Plan 1 Chat 闭环所需的最小工程能力，不实现 `P1-M4-S4` 及后续 Step，也不提前引入 Plan 4 Trace、事件总线、重试、fallback、Metrics 服务或 Observability 页面。

## 2. 已确认决策

1. 采用分层增量方案：Service 负责调用统计，Provider 负责错误分类，API 负责错误契约，ASGI 中间件负责 request ID 和请求日志。
2. 普通 HTTP 和 SSE 使用相同的结构化错误对象。
3. request ID 始终由服务端生成 UUID；忽略客户端传入的 request ID。
4. 客户端只接收分类后的安全错误消息；Provider 原始错误正文和数据库细节不进入响应。
5. 使用 Python 标准库 `logging`，不新增依赖。
6. 仅成功回合持久化 `LLMCall`；失败、空流和取消继续回滚整个 Chat 回合。

## 3. 架构边界

### 3.1 Usage 与成本计算

新增一个独立的 usage/cost helper，负责把 Provider 的 `TokenUsage` 和 Model Registry 的 `Decimal` 价格转换为 `LLMCall` 可持久化字段。Chat Service 调用该 helper，但不在 route 中计算指标。

成本公式：

```text
estimated_cost =
    (input_tokens × input_price_per_1m
     + output_tokens × output_price_per_1m)
    / 1_000_000
```

规则：

- 使用 `Decimal` 完成计算，按 `Numeric(18, 8)` 的数据库精度舍入到 8 位小数。
- Provider 未返回 usage 时，所有 token 字段和 cost 均保持 `null`。
- 任一输入/输出价格为 `null` 时，cost 保持 `null`，不猜测价格。
- 显式配置为零的价格是有效价格，cost 应为零。
- token 值直接使用 Provider 已规范化的 usage，不在本批自行估算。
- 成本使用请求所选择的 Registry 条目计算；`LLMCall.provider/model` 保持现有成功响应语义，避免改变 M3 API 行为。

### 3.2 Latency 定义

- 非流式 latency 从调用 `provider.chat()` 前开始，到成功返回或抛出 Provider 异常时结束。
- 流式 latency 统计等待 Provider 产生各 chunk 的时间，并排除外层 SSE 消费者暂停造成的等待。
- 使用单调时钟，最终保存非负整数毫秒。
- `LLMCall.latency_ms` 只在成功回合持久化；失败 latency 仅用于安全日志。
- latency 不包含数据库提交、HTTP 序列化或前端渲染时间。

### 3.3 成功与事务

非流式成功流程：

```text
校验 Registry / Provider
-> 创建或加载 Conversation
-> 追加 user Message
-> 计时并调用 Provider
-> 计算 usage / cost / latency
-> 追加 assistant Message
-> 写入 completed LLMCall
-> 更新成功回合元数据
-> 由请求依赖提交事务
```

流式成功流程：

```text
校验 Registry / Provider
-> 创建或加载 Conversation
-> 追加 user Message
-> 逐次等待 Provider chunk 并累计内容、usage、latency
-> 追加 assistant Message
-> 写入 completed LLMCall
-> 更新成功回合元数据
-> commit
-> 发送 done SSE
```

Provider 失败、空流、消费者提前关闭或数据库失败时，不保留本轮 Conversation、Message 或 `LLMCall` 的未提交变更。失败调用依靠日志和 request ID 定位，不在本批引入独立失败记录。

## 4. 错误分类

Provider 层提供以下安全异常：

| 异常 | 来源 |
|---|---|
| `ProviderConfigurationError` | 本地 Provider 配置或 API key 缺失 |
| `ProviderAuthError` | 上游 HTTP 401 / 403 |
| `ProviderRateLimitError` | 上游 HTTP 429 |
| `ProviderTimeoutError` | 连接、读取或上游超时 |
| `ProviderBadRequestError` | 上游拒绝请求 |
| `ProviderServerError` | 上游 HTTP 5xx |
| `ProviderResponseError` | 成功响应或流式 chunk 无法解析 |
| `ProviderUnknownError` | 无法安全归入其他类别的 Provider 故障 |

`ProviderRequestError` 保留为所有上游请求类错误的共同父类，认证、限流、超时、错误请求、服务故障和未分类请求错误从它派生；`ProviderResponseError` 继续表示已收到成功响应但内容无效。这样既保留已有捕获边界，也允许 API 精确分类。

OpenAI-compatible adapter 不把上游错误正文拼接到异常消息中。异常只携带分类所需的安全元数据，例如上游状态码；API key、响应正文和完整请求内容不得进入异常字符串。

## 5. 统一错误契约

### 5.1 普通 HTTP

```json
{
  "error": {
    "code": "provider_timeout",
    "message": "The model provider timed out",
    "request_id": "f9ed846d-c48b-4522-92e7-103258876ade"
  }
}
```

响应头同时返回：

```text
X-Request-ID: f9ed846d-c48b-4522-92e7-103258876ade
```

### 5.2 SSE

流式响应开始后不能修改 HTTP 状态，因此终止错误通过同构 SSE payload 返回：

```text
event: error
data: {"error":{"code":"provider_timeout","message":"The model provider timed out","request_id":"f9ed846d-c48b-4522-92e7-103258876ade"}}
```

SSE payload 的 `request_id` 必须和初始响应头的 `X-Request-ID` 相同。

### 5.3 HTTP 状态映射

| 场景 | HTTP 状态 | code |
|---|---:|---|
| 请求校验失败 | 422 | `validation_error` |
| Conversation 不存在 | 404 | `conversation_not_found` |
| Registry 模型不存在 | 400 | `model_not_found` |
| Provider 未配置或本地 API key 缺失 | 503 | `provider_unavailable` |
| Provider 认证失败 | 502 | `provider_auth_error` |
| Provider 限流 | 429 | `provider_rate_limit` |
| Provider 超时 | 504 | `provider_timeout` |
| Provider 请求被拒绝 | 502 | `provider_bad_request` |
| Provider 服务故障 | 502 | `provider_server_error` |
| Provider 响应无效 | 502 | `provider_response_error` |
| 未分类 Provider 故障 | 502 | `provider_unknown_error` |
| SQLAlchemy 数据库异常 | 503 | `database_error` |
| 其他 HTTP 404 / 405 等 | 原 HTTP 状态 | `http_error` |
| 未预期异常 | 500 | `internal_error` |

对 FastAPI 请求校验、Starlette/FastAPI HTTP 错误、已知业务错误、Provider 错误、SQLAlchemy 错误和未预期异常注册统一 handler。共享错误映射函数把异常转换为 `status/code/message`，普通 HTTP handler 和流内 SSE 捕获逻辑共同使用它，避免两套分类漂移。上游 HTTP 408 / 504 归入 Provider timeout。流内 SQLAlchemy 错误也发送 `database_error` SSE。客户端消息使用固定安全文本，不返回 SQL、数据库路径、上游正文、堆栈或配置值。

前端 HTTP 与 SSE 解析器优先读取新结构，同时兼容既有 `detail` 和 SSE `message`，防止尚未迁移的响应失去错误提示。

## 6. Request ID 与中间件

使用纯 ASGI 中间件，而不是依赖 `BaseHTTPMiddleware`。中间件生命周期覆盖整个流式响应，可确保 ContextVar 在最后一个 SSE chunk 发送前保持有效。

每次请求：

1. 生成新的 UUID request ID。
2. 写入 request-scoped ContextVar。
3. 拦截 `http.response.start` 并追加 `X-Request-ID`。
4. 在整个 ASGI 调用结束后记录请求完成日志。
5. 最终恢复 ContextVar，避免请求间串值。

客户端传入的 `X-Request-ID` 不复用、不回显。

## 7. 日志设计

### 7.1 格式

使用 Python 标准库 `logging` 输出单行 `key=value` 日志。基础字段包括时间、级别、logger、event 和 request ID。无请求上下文时 request ID 为 `-`。

请求日志至少包含：

- `event=request_completed`
- `request_id`
- `method`
- `path`，不记录 query string
- `status_code`
- `duration_ms`

模型日志至少包含：

- `event=llm_call_completed` / `llm_call_failed` / `llm_call_cancelled`
- `request_id`
- `provider`
- `model`
- `latency_ms`
- `outcome`
- 成功时可包含 token 与 cost
- 失败时只包含安全 error code 和异常类名

### 7.2 安全规则

日志不得记录：

- 请求或响应 body
- 完整用户消息或 assistant 内容
- Authorization header 或其他请求 headers
- API key、token 或 Provider credential
- Provider 原始错误正文
- SQL 参数、数据库路径或可能包含消息内容的异常字符串

已知 Provider 和数据库错误不直接使用会格式化异常文本的 `logger.exception()`。如需定位调用位置，只记录从 traceback 提取的文件名、函数名和行号，不记录异常消息、局部变量或 SQL 参数。

## 8. 测试策略

实施按 TDD 进行，先写失败测试，再实现最小代码。

### 8.1 Pure logic

- 正常 token/价格计算
- 零价格
- 任一价格为 `null`
- usage 缺失
- 8 位小数舍入

### 8.2 Service 与事务

- 非流式成功持久化 provider/model/tokens/cost/latency
- 流式成功持久化同样字段
- Provider 失败回滚
- 空流回滚
- 客户端提前关闭回滚
- 成本未知时持久化 `null`

### 8.3 Provider

- 401/403、429、400、5xx 分别映射到明确异常
- `httpx` 超时映射为 `ProviderTimeoutError`
- 非超时 transport error 映射为安全的未分类请求错误
- 成功响应格式错误映射为 `ProviderResponseError`
- 模拟 API key 和上游敏感原文不出现在异常或日志中

### 8.4 API 与 SSE

- 每个响应都有服务端生成的 `X-Request-ID`
- 结构化错误体中的 request ID 与响应头一致
- 客户端传入的 request ID 被忽略
- API key 缺失、Provider 错误、数据库错误和未预期错误均返回安全响应
- 请求校验错误使用统一结构
- SSE error payload 与响应头使用同一 request ID

### 8.5 日志与前端兼容

- 请求日志包含 request ID、method、path、status 和 duration
- 模型日志包含 request ID、model 和 latency
- 测试日志不包含模拟 API key 或完整消息内容
- 前端可解析结构化 HTTP/SSE 错误，并保留旧格式兜底

### 8.6 批次验证

- 后端全量 pytest
- 全新临时 SQLite 的 Alembic upgrade/current/check
- `pip check`
- 前端 typecheck、tests、production build
- Uvicorn/OpenAPI smoke（不调用真实 Provider）
- `git diff --check`
- secret 与生成物扫描

## 9. 文档与计划边界

本批同步：

- 本设计文档
- 对应实施计划
- 与实际行为直接相关的架构、Provider 说明和执行步骤状态

`P1-M4-S4～S6` 的集中补测、前端基础 UI 修正和 Plan 1 文档收尾仍留给下一批。当前测试只覆盖 S1～S3 新增行为及必要回归，不将后续 Step 提前标记完成。

## 10. 已知限制

- Provider 不返回 usage 时，本批不自行 tokenize，token 和 cost 保持 `null`。
- Registry 价格为 `null` 时不计算成本；价格维护仍依赖配置准确性。
- SSE 在响应开始后的错误只能通过 `event:error` 表达，HTTP 状态仍为 200。
- 基础日志不是 Trace，不提供持久化、查询、Timeline、Replay 或跨服务传播。
- 失败调用不写 `LLMCall`，只能通过 request ID 和日志定位；独立失败记录属于后续可观测性设计。
