# Plan 3 M1/M2 整体审核修复设计

## Status

- Scope: `P3-M1` 与 `P3-M2` 已交付能力的整体审核和修复
- Date: 2026-08-01
- Selected approach: 均衡的正确性与安全加固
- Design approval: 用户已逐段确认
- Implementation status: complete; full verification passed, with current
  Docker runtime health not checked because the local daemon was unavailable

## 1. 背景与目标

Plan 3 Milestone 1 和 Milestone 2 已完成 Knowledge Base、Document 上传、
Markdown/TXT/PDF 解析、文本清洗、Naive Chunking 与同步处理流水线。本次审核在不进入
Milestone 3 的前提下，修复跨批次检查中确认的配置暴露、路径边界、Markdown 元数据、
资源放大、删除语义与数据库完整性问题，并补齐测试和文档。

本批次不读取、迁移、删除或重建 `backend/ai_agent_lab.db`。所有数据库验证使用新建的
临时 SQLite；所有文件测试使用临时目录和合成内容；不调用真实 Provider、付费服务或
网络 Tool。SQLite 继续作为默认且长期支持的主数据库，Qdrant 只保留 Plan 3 向量存储
职责。

## 2. 审核结论与选择

### 已确认问题

1. Compose 将 Qdrant `6333` 端口绑定到所有主机接口，与本地优先和文档安全声明不一致。
2. Settings 提前 `resolve()` 文档存储根目录，导致根 symlink 的证据在
   `DocumentStorage` 校验前消失。
3. Windows 上的反斜杠可以绕过 stored path 的“两段 Posix 路径”语法检查。
4. Markdown 清洗会压缩 fenced code block 内部空行，只重映射 heading 行号，造成
   code block 行号和重复保存的 `content` 元数据过期。
5. Chunk heading 可以超过 ORM/Schema 的 512 字符契约。
6. 极端 chunk size/overlap、PDF 展开量、Markdown 结构数量和提取字符数没有明确上限，
   小输入也可能放大为大量内存对象和数据库行。
7. 删除包含 Document 的 Knowledge Base 会依靠级联删除数据库记录，却遗留受控存储文件。
8. `RagQuery.answer_message_id` 的 ORM 删除行为与数据库直接删除行为不一致。
9. 同一 Knowledge Base 内的相同文件哈希只有查询式防重，没有数据库最终唯一性保护。
10. Plan 3 执行步骤表的 M2 批次状态仍保留未完成文字，与已完成记录不一致。

### 采用方案：均衡加固

修复所有已确认且能在 M1/M2 边界内闭合的问题；为资源使用增加显式上限；用补丁迁移
收紧数据库约束；保持现有同步上传、可审计失败 Document 和薄 API route。该方案不引入
后台任务、流式持久化或后续 RAG 能力。

未采用只修显性错误的最小方案，因为它会继续保留可稳定触发的资源放大和数据库竞态缺口。
未采用深度重构方案，因为异步卸载、队列和新的 ingestion 架构会扩大回归面并靠近后续
Step 的职责。

## 3. 范围

### Included

- Qdrant 仅绑定本机回环地址；
- 文档存储根目录和 stored path 的跨平台安全边界；
- Markdown fenced code block 的清洗与结构元数据一致性；
- heading、PDF、文本、Markdown 结构和 chunk 数量上限；
- 非空 Knowledge Base 的安全 409 删除契约；
- 同 Knowledge Base 文件哈希唯一性；
- RagQuery/Message 的数据库删除一致性；
- ORM、Alembic、Settings、service、API、测试和正式文档的同步更新。

### Excluded

- Document list/detail/delete/retry/reprocess API；
- background worker、queue、polling、cancel 或 progress streaming；
- Embedding Provider、Qdrant collection/point/vector 写入；
- Retriever、RAG Prompt、RAG query/chat、Agent Tool 或前端 Knowledge Base 工作台；
- OCR、布局分析、表格重建、图片提取和多模态；
- Advanced RAG、Hybrid Search、Rerank、Evaluation、Memory 或 Plan 4+ 能力；
- PostgreSQL 迁移、分布式锁或围绕假想多用户并发的架构改造。

## 4. 配置与存储安全

### Qdrant

Compose 端口声明由 `6333:6333` 改为 `127.0.0.1:6333:6333`。测试验证解析后的
Compose 配置和跟踪文本都没有对所有主机接口暴露。运行时 health 只在 Docker daemon
确实可访问且无需下载镜像时验证；不能访问 daemon 时明确记录限制，不伪造健康证据。

### 文档存储根目录

Settings 只把配置路径转换为绝对词法路径，不解析 symlink/reparse target。创建目录、根目录
symlink/reparse 检查、祖先链检查和 containment 继续由 `DocumentStorage` 负责。这样配置层
不会在安全层校验前擦除路径性质。

### Stored path 语法

内部存储路径只接受精确格式：

```text
<knowledge_base_uuid>/<document_uuid>.<md|txt|pdf>
```

校验必须拒绝：

- 反斜杠或混合分隔符；
- 绝对路径、盘符、UNC、空段、`.` 或 `..`；
- 多余目录层级；
- 非规范 UUID、后缀或字符串 round-trip 不一致；
- ownership UUID 或 file type 与调用参数不一致；
- root、Knowledge Base 目录或目标文件为 symlink/reparse point；
- 缺失、非普通文件或解析后逃逸受控根目录。

绝对路径只供内部 parser 使用，不能进入响应、错误、日志或 Document 元数据。

## 5. Markdown 清洗与元数据

Cleaner 继续对 Markdown 正文执行换行和控制字符策略，但 fenced code block 的内部空行数量
必须保持，不参与普通段落的连续空行折叠。代码围栏、缩进、标签与非空正文保持原样；围栏
外仍将连续空白行折叠为一个空段落。

Parser/cleaner 的 code block 元数据只保留小型结构字段：

```text
language
start_line
end_line
```

不再把完整 code `content` 复制进 Document metadata。完整代码仍存在
`ParsedDocument.text`，调用方可以使用行号定位；去除副本可避免大文件双倍保存并杜绝清洗后
正文与 metadata 内容不一致。

Cleaner 在完成换行清理和空行策略后同时重映射 heading 与 code block 的行号。行号均指向
清洗后文本，且 code block 的 `start_line`/`end_line` 包含 opening/closing fence。TXT/PDF
不创建 Markdown 专用的逐行映射；PDF page 继续独立清洗并保留页号。

## 6. 处理资源上限

新增一个可注入、不可变的 Document processing limits 契约，由 Settings 提供以下默认值：

| Environment variable | Default | Meaning |
|---|---:|---|
| `DOCUMENT_MAX_PDF_PAGES` | `500` | 单个 PDF 可处理的最大页数 |
| `DOCUMENT_MAX_EXTRACTED_CHARACTERS` | `10000000` | 单个文档累计可处理字符数 |
| `DOCUMENT_MAX_MARKDOWN_STRUCTURES` | `20000` | heading 与 code block 的合计上限 |
| `DOCUMENT_MAX_CHUNKS` | `10000` | 单个文档可生成的最大 chunk 数 |

所有值必须是正整数，并设置配置解析上界，防止错误环境变量取消保护：PDF 页数最多
`10000`、提取字符最多 `100000000`、Markdown 结构最多 `100000`、chunks 最多
`100000`。现有
`DOCUMENT_MAX_UPLOAD_BYTES` 继续负责原始上传字节数，以上限制负责解析后的放大边界。

执行位置：

- PDF parser 在提取正文前检查页数，并在逐页提取时累计字符数；
- TXT/Markdown 在解码后、构造大规模衍生结构前检查字符数；
- Markdown parser 在追加 heading/code block 时增量检查结构数量；
- Chunker 在物化所有 draft 前计算或增量限制 chunk 数，并保证超限后不返回部分结果；
- 写入 `DocumentChunk` 前将 heading 截断为最多 512 个 Python 字符，与 ORM/Schema 契约一致。

资源限制属于预期内容处理失败。Document 保留并进入安全的 failed 状态，不持久化部分
chunks；错误消息使用固定文案，不包含正文、文件名、绝对路径、页内容或内部异常。

## 7. Knowledge Base 删除契约

用户选择安全拒绝策略：当 Knowledge Base 存在任意 Document（包括处理失败的 Document）
时，删除请求返回 HTTP 409，并保持 Knowledge Base、Document、DocumentChunk 与存储文件
不变。

Service 先执行存在性查询并抛出 `KnowledgeBaseNotEmptyError`，API 将其映射为稳定 409。
数据库把 `documents.knowledge_base_id` 的删除行为从级联改为限制，ORM 关系同步取消对
Document 的自动删除级联并使用 `passive_deletes="all"`，作为竞争或绕过 service 时的最终
保护。数据库约束冲突同样归一化为不泄露细节的 409。

空 Knowledge Base 仍可删除。本批次不扫描或删除没有数据库归属的历史孤儿文件，也不增加
Knowledge Base 目录清理器。

## 8. 数据库完整性与迁移

新增 Alembic 补丁 revision，不改写已提交的 `20260726_0005`。

### 同 Knowledge Base 文件哈希唯一性

在 `documents` 增加 `(knowledge_base_id, file_hash)` 唯一约束。Service 的查询式防重继续
提供快速、可读的常规错误；唯一约束负责并发竞争的最终一致性。插入 flush 命中该约束时，
本次事务回滚、暂存文件清理，并归一化为现有重复文档 409，不暴露 SQL 或约束名。

迁移先进行不含文件内容和路径的重复计数检查。若历史库已存在重复组合，则 fail-closed，
只报告需要人工检查的记录组数量，不自动删除、合并或选择保留项。

### RagQuery answer Message

为 `rag_queries.answer_message_id` 增加独立的
`messages.id ON DELETE SET NULL` 外键，同时把
`(answer_message_id, conversation_id) -> messages(id, conversation_id)` 的归属复合外键从
`ON DELETE RESTRICT` 改为 `ON DELETE NO ACTION`。SQLite 的 `RESTRICT` 会在单列外键执行
`SET NULL` 前立即拒绝删除；`NO ACTION` 则在语句结束时检查，此时 answer ID 已为空而
conversation ID 保持不变。复合外键仍会拒绝跨会话 answer 关联，RagQuery 审计记录得以
保留，且 ORM 删除和数据库直接删除产生同一结果。

### Migration 行为

迁移使用 Alembic batch operations 保持 SQLite 支持，同时更新 ORM metadata。升级、降级、
重新升级都只在新建临时 SQLite 上验证；downgrade 移除单列 answer 外键、把复合外键恢复为
`RESTRICT`，并恢复原 Document 级联与唯一性结构，不修改业务数据。绝不对用户数据库执行
本次验证。

## 9. 上传数据流与错误契约

现有同步数据流保持不变：

```text
API schema validation
  -> stage controlled file
  -> promote into controlled storage and register rollback cleanup
  -> create pending Document and flush ownership/hash constraints
  -> parse with limits
  -> clean
  -> chunk with limit
  -> persist ordered chunks
  -> request-owned commit
```

Parser、Cleaner、Chunker 和 ingestion service 分别持有纯逻辑或业务编排职责，route 不承载
业务判断。Session request dependency 继续作为 commit/rollback owner。

错误分为：

- 预期内容/资源错误：提交 failed Document，HTTP 201 返回可审计状态，无 chunks；
- 重复上传：HTTP 409，事务回滚并清理本次暂存文件；
- 非空 Knowledge Base 删除：HTTP 409，不修改数据库或文件；
- 存储、数据库和意外程序错误：沿用安全 5xx，事务回滚并执行现有清理回调。

固定错误不能包含用户正文、文件名、绝对路径、哈希、数据库约束名、SQL 或 parser 原始诊断。

## 10. TDD 测试矩阵

所有行为改动遵循 RED -> GREEN -> REFACTOR。

| Area | First failing evidence and final contract |
|---|---|
| Compose | 旧的全接口端口断言先失败；最终只接受 loopback bind |
| Settings/storage | 根 symlink 不再被 Settings 隐藏；Windows 混合分隔符和非规范路径被拒绝 |
| Markdown cleaner | code 内连续空行保持；heading/code block 行号准确；metadata 无正文副本 |
| Parser limits | PDF 页数、累计字符、Markdown 结构数量覆盖边界值与超限值 |
| Chunker | 在大量 draft 物化前拒绝超限；heading 最大 512 字符 |
| Ingestion | 每种限制错误形成安全 failed Document，且没有部分 chunks |
| KB service/API | 非空删除返回 409 且记录/文件不变；空 KB 仍可删除 |
| DB constraint | 原生删除非空 KB 被拒绝；同 KB 相同 hash 被唯一约束阻止 |
| Duplicate normalization | service 将唯一约束竞争归一化为 409 并清理本次暂存文件 |
| RagQuery FK | 原生 SQL 删除 Message 后 answer ID 置空、query 和 conversation ID 保留 |
| Migration | 临时 SQLite upgrade/check/downgrade/re-upgrade；重复历史数据 fail-closed |

测试不得读取真实 `.env`、secret、用户 SQLite 或工作区外文件，不调用 Docker 网络、Provider
或网络 Tool。

## 11. 文档与验证

实现完成时同步更新：

- `.env.example` 与 `backend/.env.example` 中实际存在的配置入口；
- `README.md`、`README_CN.md` 与 `CHANGELOG.md`；
- Knowledge Base、Document ingestion/processing、Qdrant 运维相关正式文档；
- Plan 3 执行步骤表的 M1/M2 状态和审核证据；
- 一份正式的 Plan 3 M1/M2 整体审核修复记录；
- 具体实施计划中的 TDD 与实际验证证据。

文档必须继续明确：M2 截止于持久化 chunks；Embedding、Qdrant 数据写入、Retriever、RAG
API、Document 查询/删除、OCR 和 frontend Knowledge Base 能力尚未实现。

最终验证包括：定向测试、backend 全量 pytest、`pip check`、临时 SQLite Alembic 全链路、
frontend typecheck/Vitest/production build、Compose 配置解析、Markdown 本地链接、secret、生成物、
later-Plan runtime、`git diff --check`、staged paths、Git 状态和 diff 范围检查。Docker daemon
不可访问时只记录运行时健康未复核，不以静态检查冒充 health 证据。

## 12. 接受限制与非适用项

### Accepted limitation

- 上传仍在请求内同步处理；本批次不引入 worker 或任务生命周期。
- 不针对能在检查后以本机特权替换路径的攻击者提供完整 TOCTOU 防御；稳定可见的
  symlink/reparse 和路径语法绕过必须封闭。
- 不自动清理历史孤儿文件，也不修复迁移前已有的重复业务数据。
- Docker daemon 或本地镜像不可用时，Qdrant 运行时 health 不是本批次可伪造的证据。

### Not applicable / later Step

- Embedding、Vector Store 写入与检索属于 M3；
- Advanced RAG、Rerank、Evaluation 属于 Plan 4；
- OCR、multimodal、Memory、MCP 和 Human Approval 属于后续 Plan；
- PostgreSQL、分布式锁与高并发部署不符合当前 local-first 单用户约束。

## 13. 完成标准

本设计列出的确定性缺陷均有先失败后通过的回归测试；ORM、迁移、service、API、配置和文档
同步；完整验证通过；没有 secret、生成物、用户数据库访问或跨 Plan runtime；Codex self-review
无未解决 must-fix 项；diff 仅包含本次 M1/M2 审核修复。满足这些条件后，M1/M2 才可重新
封板并允许用户决定是否进入 `P3-M3-S1～S3`。提交仍由用户手动完成。
