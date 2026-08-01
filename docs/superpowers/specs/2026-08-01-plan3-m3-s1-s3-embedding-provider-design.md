# Plan 3 M3 S1～S3 Embedding Provider Design

## 1. Scope And Baseline

本批只实现 `P3-M3-S1～S3`：Embedding Provider 抽象、批量结果契约和
Provider Registry。起始基线为 `main == origin/main ==
70ef2f90307a11beb8755439085ce29b1f2bc7aa`，工作区与暂存区为空。

Docker Desktop 已可访问；固定版本 `qdrant/qdrant:v1.15.4` 已通过 Compose
启动，端口只绑定 `127.0.0.1:6333`，`/healthz` 返回
`healthz check passed`。本批不创建 Qdrant client、collection 或 point。

## 2. Acceptance Matrix

| Step | 验收要求 | 当前证据 | 缺口 | 最小新增测试/实现/文档 |
|---|---|---|---|---|
| P3-M3-S1 | `providers/embedding/base.py`；mock Provider 测试通过 | 只有 `providers/llm`，无 Embedding package/runtime | 缺少可替换的 Embedding 抽象和 query/batch 接口 | 创建 `EmbeddingProvider` 与 mock contract 测试 |
| P3-M3-S2 | `EmbeddingResult`；batch 输入返回向量和 token usage | Knowledge Base 仅有 provider/model 持久化桥接字段 | 缺少不可变结果、usage、向量形状和有限数边界 | 创建 `EmbeddingUsage`、`EmbeddingResult`，覆盖 batch/query、空结果、空向量、维度不一致、NaN/Infinity 和 usage 校验 |
| P3-M3-S3 | `providers/embedding/registry.py`；可按配置选择 Provider | LLM Model Registry 管静态模型目录，Tool Registry 管 Tool 实例，均不适合直接复用 | 缺少运行时 Embedding Provider 注册、选择与稳定错误 | 创建有序实例 Registry，覆盖配置名选择、重复、缺失、类型错误和防御性列表 |

## 3. Considered Approaches

### Adopted: Dedicated Runtime Provider Registry

建立独立的 `EmbeddingProvider` 和 `EmbeddingProviderRegistry`。Provider 自带规范化
名称；Registry 保存实例并按调用方提供的配置名称精确选择。结果使用不可变 Pydantic
模型，保持与现有 Provider 边界风格一致。

该方案让后续 S4 的 OpenAI-compatible adapter 只依赖抽象，让 S5 的 Settings/初始化
逻辑只负责创建并选择实例，同时不把厂商、HTTP 或 secret 泄漏到业务层。

### Rejected: Reuse The LLM Model Registry

LLM `ModelRegistry` 管理 JSON 中的模型能力和价格元数据，不管理已初始化的运行时
Provider 实例。复用会混淆静态模型目录与可调用 adapter 的职责。

### Rejected: Add Settings And Provider Factory Now

在 S3 直接读取环境变量、创建具体 Provider 或选择默认模型会提前实现 S4～S5。当前
Registry 只接受调用方传入的配置名称；Settings 集成留在其明确 Step。

## 4. Contracts

### EmbeddingUsage

`EmbeddingUsage` 是不可变、拒绝额外字段的批级 token 统计：

- `input_tokens: int >= 0`
- `total_tokens: int >= input_tokens`

Embedding 没有生成 token，因此不复用带 `output_tokens` 的 LLM `TokenUsage`。

### EmbeddingResult

`EmbeddingResult` 是不可变、拒绝额外字段的 Provider 输出：

- `model`: 去除首尾空白后非空；
- `vectors`: 有序、非空的二维向量；
- `usage`: `EmbeddingUsage`；
- 所有向量非空、维度一致，所有数值有限；
- `dimension` 只读属性返回统一维度。

结果保持批次顺序。具体 adapter 必须保证向量数量与输入文本数量一致；S4 实现响应解析
时再在 adapter 边界核对，因为 `EmbeddingResult` 本身不持有用户正文或输入数量。

### EmbeddingProvider

`EmbeddingProvider` 是 ABC：

- 构造时接收 `name`，去除首尾空白后必须非空且不超过 100 字符；
- `async embed_texts(texts: list[str]) -> EmbeddingResult`；
- `async embed_query(query: str) -> EmbeddingResult`。

本批不规定 HTTP、重试、timeout、API key、模型维度配置或本地模型加载。

### EmbeddingProviderRegistry

Registry 提供：

- `register_provider(provider)`：只接受 `EmbeddingProvider` 实例，重复名称原子失败；
- `get_provider(name)`：配置名必须是字符串，按精确名称返回实例；
- `list_providers()`：按注册顺序返回防御性列表副本。

错误类型为 `EmbeddingProviderRegistryError`、
`DuplicateEmbeddingProviderError` 和 `EmbeddingProviderNotFoundError`。

## 5. Data Flow And Boundaries

```text
caller-owned configured provider name
  -> EmbeddingProviderRegistry.get_provider(name)
  -> EmbeddingProvider.embed_texts(...) / embed_query(...)
  -> EmbeddingResult(model, vectors, usage)
```

本批不接入 Knowledge Base service、Document ingestion、数据库状态、Qdrant、API 或
前端。业务代码因此仍不会调用 Embedding；只是建立后续步骤可依赖且可独立测试的边界。

## 6. Error And Security Behavior

- 空白/过长 Provider 名在构造时失败；Registry lookup 不做隐式大小写转换或 trim，避免
  配置拼写错误静默选择其他 Provider。
- duplicate/missing 错误只包含非敏感 Provider 名，不包含凭据、正文、向量或内部配置。
- 结果拒绝空批次、空向量、维度不一致和非有限数，防止畸形 Provider 输出进入后续向量库。
- 测试只使用内存 Mock Provider，不读取 `.env`、真实 secret、用户 SQLite 或网络。

## 7. TDD And Verification

RED 先创建 `backend/tests/test_embedding_provider.py` 与
`backend/tests/test_embedding_provider_registry.py`，确认因 package/contract 缺失而失败；
再创建最小生产实现并运行聚焦测试。之后运行相邻 Provider/Knowledge/RAG 回归、backend
全量测试、依赖检查、frontend typecheck/test/build、临时 SQLite Alembic 全链路、Compose/
Qdrant health、文档链接、secret/artifact/later-Plan 和 Git 边界检查。

## 8. Documentation Changes

同步 `README.md`、`README_CN.md`、`CHANGELOG.md`、`docs/01-architecture.md`、
`docs/20-knowledge-base-design.md` 与 Plan 3 执行步骤表。明确 S1～S3 只提供抽象、结果和
Registry；OpenAI-compatible adapter/config/error handling、Embedding 正式专题文档、
Qdrant Vector Store、向量写入、Retriever 与 RAG 仍未实现。

## 9. Self-Review

- 无 `TBD`、`TODO` 或未决接口；
- S1～S3 的交付物、验证方式和错误边界逐项覆盖；
- 未创建 S4+ 文件或配置项，未修改数据库/API/前端 runtime；
- 与现有 SQLite 主存储、Qdrant 向量存储和用户手动提交规则一致。
