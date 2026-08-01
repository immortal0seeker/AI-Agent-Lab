# Plan 3 M3 S4～S6 OpenAI-compatible Embedding 设计

## Status

- Scope: `P3-M3-S4～P3-M3-S6`
- Date: 2026-08-01
- Selected approach: 独立配置命名空间、延迟初始化、响应维度双重校验
- Design approval: 用户已要求开始执行仓库内既定 Plan 3 Step
- Implementation status: complete; full verification and Codex self-review passed

## 1. 目标

在现有厂商无关 `EmbeddingProvider`、`EmbeddingResult` 和
`EmbeddingProviderRegistry` 之上，实现一个可替换的 OpenAI-compatible HTTP
适配器。适配器必须支持批量文本和单条 query，保存服务端实际返回的模型与 token
usage，并把配置、HTTP、网络、响应格式和维度错误收敛到 Embedding Provider 边界。

本批只证明 Chunk 文本可以通过 Provider 边界转换成向量，不把 Provider 接入文档处理
流水线，也不创建 Qdrant collection、point 或 payload。

## 2. 验收映射

| Step | 验收要求 | 设计响应 |
|---|---|---|
| S4 | mock HTTP 或测试替身验证请求和响应解析 | 使用 `httpx.MockTransport` 验证 `/embeddings`、Bearer header、批量 payload、响应排序、model、usage 和 vectors |
| S5 | 缺少 key 或模型维度不匹配时返回可读错误 | `SecretStr` 配置、延迟工厂校验、专用配置错误、响应维度错误和安全 HTTP 错误层级 |
| S6 | 文档说明配置、模型、维度、成本注意事项 | 新增 `docs/21-embedding-provider.md`，同步 README、架构、知识库设计、CHANGELOG 和执行步骤表 |

## 3. 方案选择

### 采用：独立 OpenAI-compatible Embedding 配置

使用：

```text
EMBEDDING_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_EMBEDDING_BASE_URL=...
OPENAI_COMPATIBLE_EMBEDDING_API_KEY=...
OPENAI_COMPATIBLE_EMBEDDING_MODEL=...
OPENAI_COMPATIBLE_EMBEDDING_DIMENSION=...
OPENAI_COMPATIBLE_EMBEDDING_TIMEOUT_SECONDS=...
```

该方案保留 Registry 的厂商选择职责，同时避免 Embedding 与 LLM 共用 model、key 或
timeout。配置在 `Settings` 解析时只做类型和数值边界校验；只有初始化具体 Provider 时
才要求 base URL、key、model 和 dimension，避免未启用 RAG 时阻断应用启动。

未采用复用 `OPENAI_COMPATIBLE_*`，因为 LLM 与 Embedding 经常使用不同 endpoint、
模型和凭据。未采用全部泛化为 `EMBEDDING_*`，因为它会把当前适配器的 HTTP 参数泄漏
到未来不同协议的 Provider。

## 4. HTTP 契约

适配器向 `{base_url.rstrip('/')}/embeddings` 发送一次 `POST`：

```json
{
  "model": "configured-model",
  "input": ["first", "second"],
  "dimensions": 3,
  "encoding_format": "float"
}
```

`embed_query(query)` 复用相同批量路径并发送单元素数组。输入必须是非空字符串；批量
必须至少包含一项。适配器不负责 token 截断或拆批，因为具体模型限制不同，静默截断会
破坏检索语义。

成功响应必须包含 `data`、`model` 和 `usage`。每个 data item 必须有唯一、连续且处于
请求范围内的 `index`，适配器按 index 恢复输入顺序。向量必须是非空、有限、同维数的
数值数组；条目数必须与输入数一致。usage 的 `prompt_tokens` 映射为
`EmbeddingUsage.input_tokens`。

配置维度同时用于请求参数和本地响应校验。服务端即使忽略 `dimensions`，也不能让错误
尺寸的向量静默进入后续 Vector Store。模型名记录服务端实际返回值，不假设它一定与请求
别名相同。

## 5. 错误与安全边界

在 `EmbeddingProviderError` 下增加独立错误层级：

- 配置错误；
- 本地输入错误；
- 带可选 status code 的请求错误，以及 auth、rate limit、timeout、bad request、
  server 和 unknown 子类；
- 成功响应格式错误；
- 响应维度不匹配错误。

错误消息只说明错误类别、配置变量或 expected/received dimension，不拼接响应 body、
输入文本、向量或 API key。401/403、429、408/504、其他 4xx、5xx 和未分类状态分别映射
为稳定错误；`httpx.TimeoutException` 与其他 `RequestError` 也被规范化。

工厂从 `SecretStr` 取 key 后仅在内存中传入适配器。tracked 示例始终保留空 key，测试只
使用合成 key、示例域名和 `MockTransport`，不读取真实 `.env`，不发起真实 Provider 请求。

## 6. 范围边界

### Included

- OpenAI-compatible Embedding HTTP adapter；
- Embedding 专用 Settings 和初始化工厂；
- 配置、输入、HTTP、网络、响应格式与维度错误；
- mock HTTP 单元测试与正式文档。

### Excluded

- Qdrant VectorStore 抽象、collection、upsert、search 或 payload；
- 文档 chunk embedding 和 ingestion 串联；
- Retriever、RAG Prompt、RAG API、Agent Tool 或前端；
- 自动拆批、重试、缓存、计费计算或真实 Provider smoke test；
- Advanced RAG、Rerank、Evaluation、Memory、OCR、multimodal 或 Plan 4+ 能力。

## 7. 验证策略

先通过缺失模块/配置形成 RED，再实现最小 GREEN。focused 测试覆盖正常批量/query、
请求映射、乱序响应、输入和配置拒绝、密钥遮蔽、状态码、网络错误、无效 JSON、结构错误、
数量/index/维度错误与敏感信息不泄漏。最终运行 backend 全量、依赖检查、临时 SQLite
Alembic 往返、frontend typecheck/test/build、Compose/Qdrant health、文档链接、secret、
artifact、Plan boundary、`git diff --check`、staged paths 和状态检查。
