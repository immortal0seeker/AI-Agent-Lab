# Plan 3 执行步骤表｜Document Ingestion + Naive RAG

> 适用文档：`00-ALL PLAN/03-PLAN-3 (V1.0).md`  
> 执行方式：每次只领取连续 1～3 个 Step，完成后立即测试、提交、review。  
> 阶段目标：一个阶段完成一个里程碑；一个里程碑通过后再进入下一个里程碑。
> 外部复审策略覆盖（2026-07-18 用户决定）：不再使用 Claude Code；本文件后续所有 Claude Code / Claude review 节点均被此决定覆盖，不作为验收或推进门槛。每批只执行 Codex self-review；全部 6 个 Plan 和整个项目完成后，再由用户决定是否使用 Fable 5 做一次全项目检查。

---

## 0. 执行总原则

| 规则 | 说明 |
|---|---|
| 单次执行范围 | Cursor / Codex 每次只做 1～3 个连续 Step |
| 执行顺序 | 必须按 `P3-Mx-Sy` 顺序推进，除非 Codex 明确调整 |
| 每步完成定义 | 代码可运行、局部测试通过、相关文档或配置同步 |
| 每个阶段完成定义 | 阶段验收项全部通过，Codex review 后进入下一阶段 |
| Claude Code 使用时机 | 数据模型、Ingestion Pipeline、Embedding / Vector Store、Retriever / RAG API 完成后 |
| 提交节奏 | 每 1～3 个 Step 一次 commit；每个里程碑结束一次 review commit |
| 文档同步 | 文档格式、上传限制、Qdrant 配置、RAG API、来源展示变化必须同步 docs 或 README |
| 禁止提前做 | Hybrid Search、Parent-Child、Rerank、Query Rewrite、Evaluation、Memory、Agentic RAG、OCR、多模态 |

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

## 1. Plan 3 总览

| 阶段 | 里程碑 | 对应原 PLAN3 Step | 核心交付 | 预计时间 | 主要工具 | 审核节点 |
|---|---|---|---|---:|---|---|
| Phase 1 | M1 交接与知识库数据模型 | Step 1～4 | v0.2.1 补丁基线检查、Qdrant 启动、KnowledgeBase / Document / Chunk / RAG Query 模型、KB API | 15～25 h | Codex | Codex + Claude Code |
| Phase 2 | M2 文档上传与解析 Pipeline | Step 5～8 | 文件上传、Markdown / TXT / PDF 文本解析、清洗、Chunking | 15～25 h | Codex + Cursor | Codex review |
| Phase 3 | M3 Embedding 与 Vector Store | Step 9～12 | Embedding Provider、OpenAI-compatible Embedding、Qdrant Vector Store、文档入库 Pipeline | 20～30 h | Codex | Codex + Claude Code |
| Phase 4 | M4 Retriever 与 Naive RAG API | Step 13～17 | Retriever、RAG Prompt、RAG Query API、RAG Chat API、search_knowledge_base 工具 | 15～25 h | Codex | Codex + Claude Code |
| Phase 5 | M5 前端知识库与 RAG Chat | Step 18～19 | 知识库页面、文档上传 UI、RAG Chat、来源展示 | 15～25 h | Cursor + Codex | Codex review |
| Phase 6 | M6 测试、文档与封版 | Step 20～22 | RAG 测试、README、docs、截图、CHANGELOG、v0.3.0 tag | 10～20 h | Codex + Cursor | Codex + Claude Code |

---

## 2. 执行节奏表

| 执行批次 | 建议领取范围 | 批次目标 | 完成后动作 | 状态 |
|---|---|---|---|---|
| Batch 1 | P3-M1-S1～S3 | 确认 Plan2 地基，接入 Qdrant 配置 | 跑现有测试和 Qdrant health | 已完成（配置、回归与真实 Qdrant health 均通过） |
| Batch 2 | P3-M1-S4～S6 | 建立知识库核心数据模型 | 数据库迁移和模型测试 | 已完成（四模型、schema、迁移与回归均通过） |
| Batch 3 | P3-M1-S7～S9 | 实现 Knowledge Base API | API 测试与 Codex self-review M1 | 已完成（service、API、正式文档与全量回归均通过） |
| Batch 4 | P3-M2-S1～S3 | 实现文件上传和存储 | 上传 API 测试 | 已完成（受控存储、上传 API、校验、事务清理与全量回归通过） |
| Batch 5 | P3-M2-S4～S6 | 实现 Markdown / TXT / PDF 文本解析 | Parser 测试 | 已完成（三类纯 Parser、来源 metadata、安全错误与全量回归通过） |
| Batch 6 | P3-M2-S7～S9 | 实现文本清洗和 Chunking | Chunking 测试，Codex review M2 | 已完成（Cleaner、Chunker、同步 Pipeline、正式文档与全量回归通过） |
| Batch 7 | P3-M3-S1～S3 | 实现 Embedding Provider 抽象 | mock embedding 测试 | 未完成 |
| Batch 8 | P3-M3-S4～S6 | 实现 OpenAI-compatible Embedding 和配置 | provider 测试 | 未完成 |
| Batch 9 | P3-M3-S7～S9 | 实现 Qdrant Vector Store | vector store 测试 | 未完成 |
| Batch 10 | P3-M3-S10～S12 | 实现文档入库 Pipeline | 端到端入库测试，Codex + Claude review M3 | 未完成 |
| Batch 11 | P3-M4-S1～S3 | 实现 Retriever 和 RAG Prompt | 检索 + prompt 测试 | 未完成 |
| Batch 12 | P3-M4-S4～S6 | 实现 RAG Query / Chat API | API 测试 | 未完成 |
| Batch 13 | P3-M4-S7～S8 | 注册 search_knowledge_base 工具 | Agent 工具调用测试，Codex + Claude review M4 | 未完成 |
| Batch 14 | P3-M5-S1～S3 | 实现知识库页面和上传 UI | 浏览器手测 | 未完成 |
| Batch 15 | P3-M5-S4～S6 | 实现 RAG Chat 和来源展示 | 浏览器手测，Codex review M5 | 未完成 |
| Batch 16 | P3-M6-S1～S6 | 测试、文档、截图、封版 | Codex + Claude final review | 未完成 |

---

## 3. Phase 1｜M1 交接与知识库数据模型

阶段目标：

```text
确认 v0.2.1 Tool Calling 补丁底座稳定，启动 Qdrant，并建立 Knowledge Base、Document、DocumentChunk、RAG Query 的数据模型和基础 API。
```

阶段验收：

```text
1. Plan 2 的 Tool Registry、read_file、list_dir、Simple Agent Loop 仍可用
2. Qdrant 可以通过 Docker Compose 或本地配置启动
3. knowledge_bases / documents / document_chunks / rag_queries 数据模型可用
4. Knowledge Base API 可以创建、查询、更新、删除知识库
5. 数据模型保留 Plan 4 需要的 metadata / status / hash / vector_id 扩展点
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M1-S1 | 检查 Plan 2 封版状态、v0.2.0 历史 tag 和当前 v0.2.1 tag | Codex | Plan 2 验收记录 | Chat、Tool Registry、read_file、list_dir、Agent API 均可用或有明确证据，v0.2.1 指向当前基线 | Codex |
| P3-M1-S2 | 配置 Qdrant 服务和环境变量 | Codex | `docker-compose.yml`、`.env.example`、Qdrant settings | Qdrant health 可访问 | Codex |
| P3-M1-S3 | 创建 RAG / Knowledge 目录结构 | Codex | `backend/app/rag/`、`backend/app/knowledge/` 或约定目录 | 目录结构符合 PLAN3 推荐边界 | Codex |
| P3-M1-S4 | 创建 KnowledgeBase ORM / schema | Codex | `KnowledgeBase` 模型和 schema | 模型测试通过 | Codex |
| P3-M1-S5 | 创建 Document ORM / schema | Codex | `Document` 模型和 schema | 支持 filename、file_type、file_path、hash、parse_status、metadata | Codex |
| P3-M1-S6 | 创建 DocumentChunk 和 RagQuery ORM / schema | Codex | `DocumentChunk`、`RagQuery` 模型和 schema | 包含 document_id、chunk_index、content、metadata、vector_id | Claude Code 可审 |
| P3-M1-S7 | 实现 Knowledge Base Service | Codex | `knowledge_base_service.py` | 创建、列表、详情、更新、删除测试通过 | Codex |
| P3-M1-S8 | 实现 Knowledge Base API | Codex | `api/v1/knowledge_bases.py` | API 测试通过，OpenAPI 可见 | Codex |
| P3-M1-S9 | 完成 M1 review 和数据模型文档 | Codex | `docs/20-knowledge-base-design.md` 初版 | 文档说明表结构、状态字段、扩展点 | Codex + Claude review |

### P3-M1-S1～S3 交接、Qdrant 配置与目录边界验收记录（2026-07-26）

| 验收项 | 结果与证据 |
|---|---|
| S1 Git 与发布基线 | 执行前 `main` 工作区和暂存区为空；`HEAD == origin/main == v0.2.1^{}` 为 `872310b4dc1b78e2a2487303699d68ec8b22f88b`；`v0.2.0^{}` 仍为 `0e3f3a66e1322c565f2056696f7e482cedbb5f6c`，未移动或改写既有历史。 |
| S1 Plan 2 桥接 | Tool Registry、`read_file`、`list_dir`、Simple Agent、Agent API、release version 和 `web_fetch` 延期聚焦回归为 `322 passed, 1 warning`；warning 是既知 Starlette TestClient/httpx 弃用提示。 |
| S2 RED / GREEN | 首轮配置/目录测试为 `5 failed, 8 passed`，失败原因正是缺少 `qdrant_url`、Compose 与两个包；最小实现后为 `13 passed`。 |
| S2 配置 | 根 `docker-compose.yml` 固定 `qdrant/qdrant:v1.15.4`、使用 `qdrant_data` 命名卷，并通过 `QDRANT__TELEMETRY_DISABLED=true` 禁用遥测；M1/M2 审计后将 6333 严格绑定为 `127.0.0.1:6333:6333`。后端 Settings 与 `.env.example` 提供 `QDRANT_URL=http://localhost:6333`。SQLite 仍是业务与审计主数据库。 |
| S2 runtime 复验 | 安装并启动 Docker Desktop 后，Docker Desktop `4.83.0`、Engine `29.6.2`、Compose `5.3.1` 成功启动固定版本容器；容器运行、重启次数为 0，日志报告 `Telemetry reporting disabled`，`/healthz` 返回 HTTP 200 和 `healthz check passed`。 |
| S3 目录边界 | 只新增 `backend/app/knowledge/__init__.py` 与 `backend/app/rag/__init__.py`，分别声明结构化知识编排和 Naive RAG 流水线 ownership；未创建 ORM、schema、migration、service、API、parser、Embedding、Vector Store 或前端 RAG 文件。 |
| 完整回归 | Backend `507 passed, 1 warning`，`pip check` 无破损依赖；Frontend `18 files / 90 tests`、typecheck、production build（1813 modules）通过。 |
| SQLite migration | 仅对新建系统临时 SQLite 执行 `upgrade head`、`current --check-heads`、`alembic check`；head 为 `20260720_0004`，无新 migration，临时目录已验证并删除。未读取、迁移或重建用户数据库。 |
| 文档、安全与边界 | 81 个 Markdown、67 个本地链接/图片、0 missing；新增行高置信 secret 命中 0；generated/database artifact、`web_fetch` runtime、新包中的 later-Plan runtime、真实 Provider host 命中均为 0。 |

**结论：** `P3-M1-S1～S3` 与 Batch 1 完成。Qdrant 配置与真实 runtime
health 均已验收，且本地开发配置已禁用遥测。下一批可进入
`P3-M1-S4～S6`，本批没有提前实现这些数据模型步骤。

### P3-M1-S4～S6 知识库核心数据模型验收记录（2026-07-26）

| 验收项 | 结果与证据 |
|---|---|
| 执行基线 | 开始时 `main` 工作区与暂存区为空，`HEAD == origin/main == dbdda4416b548ed805d1d3f1421f21a81c830f88`；未切换分支、移动标签或改写历史。 |
| ORM TDD | RED 因四个模型尚不存在而在 collection 阶段 ImportError；最小实现后模型测试 `19 passed`。 |
| Schema TDD | RED 因新 schema exports 尚不存在而在 collection 阶段 ImportError；实现三个 schema 模块后，模型与 schema 聚焦测试 `48 passed`。 |
| Migration TDD | RED 为 `1 failed, 1 passed`，失败原因正是四张表不存在；新增 revision `20260726_0005` 后迁移测试 `2 passed`，含既有迁移的聚焦集合为 `57 passed`。 |
| 数据模型 | 新增 `KnowledgeBase`、`Document`、`DocumentChunk`、`RagQuery` 四个独立 ORM/schema 契约；包含 ownership、状态、SHA-256 hash、metadata、vector ID、检索片段快照和回答 Message 关联字段。 |
| 关系完整性 | 知识库删除级联 Document/Chunk/RagQuery；DocumentChunk 使用 `(document_id, knowledge_base_id)` 复合外键阻止跨知识库归属；RagQuery 使用回答 Message/Conversation 复合外键阻止跨会话关联，单独删除回答 Message 时保留查询并清空引用。 |
| SQLite migration | 仅对新建系统临时 SQLite 执行 `upgrade head`、`current --check-heads` 与 `alembic check`；head 为 `20260726_0005`，无待生成操作，临时目录已验证并删除。未读取、迁移、删除或重建 `backend/ai_agent_lab.db`。 |
| 完整回归 | Backend `558 passed, 1 warning`，warning 为既知 Starlette TestClient/httpx 弃用提示；`pip check` 无破损依赖。Frontend `18 files / 90 tests`、typecheck、production build（1813 modules）通过。 |
| 范围边界 | 未新增 Knowledge Base service/API、upload/storage、parser、Chunking、Embedding、Qdrant client/Vector Store、Retriever、前端 RAG 或任何 Plan 4+ runtime；`docs/20-knowledge-base-design.md` 仍留给 S9。 |
| 文档、安全与仓库门禁 | 83 个 Markdown、67 个本地链接/图片、0 missing；新增行高置信 secret、真实 Provider host、`web_fetch` runtime、later-Plan runtime、越界路径和 generated/database artifact 命中均为 0。`git diff --check` 无发现，暂存路径 0，`HEAD == origin/main == dbdda4416b548ed805d1d3f1421f21a81c830f88`。 |
| Codex self-review | must fix：补上 Conversation 删除级联 RagQuery 的独立回归，单测与后端全量均通过；later Step：S7 service/update schema、S8 API、S9 正式模型文档；accepted limitation：保留既知 TestClient warning，且本批不提供运行时 CRUD/摄取/检索能力；not applicable：Claude/Fable 外部 review 与 Advanced RAG 等后续 Plan 能力不适用于本批。无剩余阻塞项。 |

**结论：** `P3-M1-S4～S6` 与 Batch 2 完成。当前数据模型、schema、
迁移和验证证据可支持下一批进入 `P3-M1-S7～S9`；本批未提前实现下一批内容。

### P3-M1-S7～S9 Knowledge Base Service、API 与 M1 review 验收记录（2026-07-26）

| 验收项 | 结果与证据 |
|---|---|
| 执行基线 | 开始时 `main` 工作区与暂存区为空，`HEAD == origin/main == 13e0cba4313580195da3e26c9ab1240a68d1dcfb`；未切换分支、移动标签或改写历史。 |
| Schema TDD | RED 因 `KnowledgeBaseUpdate` 尚不存在而在 collection 阶段 ImportError；实现部分更新、至少一个字段、非空 `name`/`vector_store` 和 `extra=forbid` 后为 `35 passed`。 |
| Service TDD | RED 因 `KnowledgeBaseNotFoundError` 与 service 尚不存在而在 collection 阶段 ImportError；实现 create/list/detail/update/delete、确定性排序和仅 flush 的事务边界后，schema/service 聚焦集合为 `41 passed`。 |
| API TDD | RED 为 `13 failed, 1 warning`，失败原因正是路由与 404 映射尚不存在；新增五个复数 kebab-case 路由、依赖与安全错误映射后，schema/service/API 聚焦集合为 `54 passed, 1 warning`。 |
| CRUD 契约 | `POST` 201、集合/详情 `GET` 200、部分 `PATCH` 200、`DELETE` 204 空响应；显式 `null` 可清空 nullable 字段但不能清空 `name`/`vector_store`，未知详情/更新/删除统一返回不泄露 UUID 的 `knowledge_base_not_found`。 |
| 聚焦验证 | schema、四模型、migration、service 与 API 的匹配集合为 `76 passed, 1 warning`。 |
| 完整回归 | Backend `583 passed, 1 warning`，warning 为既知 Starlette TestClient/httpx 弃用提示；`pip check` 为 `No broken requirements found`。Frontend `18 files / 90 tests`、typecheck、production build（1813 modules）通过。 |
| SQLite migration | 仅对新建系统临时 SQLite 执行 `upgrade head`、`current --check-heads` 与 `alembic check`；head 为 `20260726_0005`，无新 upgrade 操作，临时根目录已验证删除。未读取、迁移、删除或重建 `backend/ai_agent_lab.db`。 |
| 文档与当前事实 | 新增 `docs/20-knowledge-base-design.md`，同步 README、架构、CHANGELOG 与活动 Plan；86 个 Markdown、69 个本地链接/图片、0 missing。当前完成范围止于 `P3-M1-S9`，未声称 Plan 3 整体完成。 |
| 安全、边界与仓库门禁 | 21 个变更路径全部属于 S7～S9 allowlist；新增行高置信 secret、真实 HTTP host、`web_fetch` production、later/deferred runtime 路径命中均为 0；generated/database artifact 候选 0；`git diff --check` 无发现、暂存路径 0。`HEAD == origin/main == 13e0cba4313580195da3e26c9ab1240a68d1dcfb`；`v0.2.0^{}` 与 `v0.2.1^{}` 仍分别为 `0e3f3a66e1322c565f2056696f7e482cedbb5f6c`、`872310b4dc1b78e2a2487303699d68ec8b22f88b`。 |
| Codex self-review | must fix：文档编辑阶段纠正 README 重复短语，并移除对不存在 `docs/05-api.md` 的计划路径；修正后文档门禁与回归通过，无剩余 must-fix。later Step：M2 upload/storage/Document API 与解析/Chunking，M3 Embedding/Qdrant client，M4 Retriever/RAG runtime，M5 前端。accepted limitation：保留既知 TestClient warning；M1 列表无分页/搜索/计数，删除仅处理 SQLite metadata，不执行 Qdrant side effect。not applicable：Claude/Fable 外部 review、Advanced RAG/Rerank/Evaluation/Memory/OCR/multimodal 均不适用于本批。 |

**结论：** `P3-M1-S7～S9`、Batch 3 与 M1 完成；当前证据支持下一批进入
`P3-M2-S1～S3`。本批未开始 Document upload/storage/API、解析、Chunking、
Embedding、Qdrant client、Retriever、前端 RAG 或任何 Plan 4+ runtime。

M1 完成后建议 commit：

```text
feat(rag): add knowledge base models and api
```

---

## 4. Phase 2｜M2 文档上传与解析 Pipeline

阶段目标：

```text
实现文档上传、文件存储、Markdown / TXT / PDF 文本解析、文本清洗和基础 Chunking。
```

阶段验收：

```text
1. 可以上传 Markdown / TXT / 文本型 PDF
2. 文档文件保存到受控目录
3. Document 记录 parse_status、file_hash、file_type、metadata
4. Parser 输出 ParsedDocument
5. Text Cleaner 和 Chunker 可单独测试
6. 解析失败不会导致系统崩溃，Document 状态可见
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M2-S1 | 实现文件上传存储策略（已完成） | Codex | `document_storage.py` | 文件保存到受控目录，文件名冲突安全处理 | Codex |
| P3-M2-S2 | 实现 Document Upload API（已完成） | Codex | `api/v1/documents.py` 上传接口 | 上传 Markdown / TXT / PDF 返回 Document 记录 | Codex |
| P3-M2-S3 | 添加文件类型、大小、hash 校验（已完成） | Codex | 上传校验逻辑 | 超大文件、未知类型、重复文件测试通过 | Codex |
| P3-M2-S4 | 实现 Markdown Parser（已完成） | Codex | `parsers/markdown_parser.py` | Markdown 标题、正文、代码块提取测试通过 | Codex |
| P3-M2-S5 | 实现 TXT Parser（已完成） | Codex | `parsers/txt_parser.py` | TXT 文本读取和编码处理测试通过 | Codex |
| P3-M2-S6 | 实现文本型 PDF Parser（已完成） | Codex | `parsers/pdf_parser.py` | 文本型 PDF 可提取文本；扫描 PDF 返回可读限制说明 | Codex |
| P3-M2-S7 | 实现 Text Cleaner（已完成） | Codex | `text_cleaner.py` | 空白、重复换行、不可见字符清洗测试通过 | Codex |
| P3-M2-S8 | 实现 Chunker（已完成） | Codex | `chunker.py` | chunk_size、overlap、chunk_index、token_count 测试通过 | Codex |
| P3-M2-S9 | 串联解析、清洗、切分并更新 Document 状态（已完成） | Codex | parser pipeline 初版 | 上传后可生成 DocumentChunk 记录 | Codex review |

### P3-M2-S1～S3 受控 Document 上传验收记录（2026-07-26）

| 验收项 | 结果与证据 |
|---|---|
| 范围与设计 | 新增已确认的设计与实施计划；本批只实现受控文件存储、一个嵌套 multipart POST、类型/大小/hash/同知识库重复校验与事务文件清理。未创建 parser、cleaner、Chunker、Embedding、Qdrant client、Retriever 或前端上传 runtime。 |
| S1 受控存储 | 默认根目录为 `backend/uploads`，相对配置从 backend root 解析；以 64 KiB read request 流式写入 `.staging`，边写边计算小写 SHA-256，最终保存为 `<knowledge_base_uuid>/<document_uuid>.<md\|txt\|pdf>` 相对 POSIX 路径。受管目录、symlink/reparse、containment、空文件、类型和 20 MiB 默认上限均有测试。 |
| S2 API 与事务 | 新增且只新增 `POST /api/v1/knowledge-bases/{knowledge_base_id}/documents`，成功返回 HTTP 201 `DocumentRead`。Route 保持薄；`DocumentService` 只 flush，由请求 Session 负责 commit/rollback；commit 失败和 rollback 会清理新提升文件。 |
| S3 校验策略 | 每个 Knowledge Base 默认最多 50 个 Document，数量检查与 Knowledge Base 404 均发生在读取 stream 之前；同一 Knowledge Base 按 SHA-256 拒绝重复，不同 Knowledge Base 允许相同内容；错误稳定映射为安全的 400/409/413/415/503。 |
| TDD RED / GREEN | config/storage RED 为缺少上传错误与存储导出；GREEN `34 passed`。service RED 为缺少 `DocumentService`；storage/service GREEN `26 passed`，相邻 config/model/schema/service 回归 `97 passed`。API RED 为 `20 failed, 1 warning`（路由与映射缺失）；API GREEN `20 passed, 1 warning`；聚焦回归 `136 passed, 1 warning`。 |
| 依赖 | 新增 `python-multipart>=0.0.18,<0.1.0`，本机安装 `0.0.32`。首次 editable install 暴露 flat-layout 自动发现 `app`/`alembic` 冲突；显式限定 setuptools `app*` 后同一安装命令成功，`pip check` 为 `No broken requirements found`。 |
| 完整回归 | Backend `635 passed, 1 warning`；warning 为既知 Starlette TestClient/httpx 弃用提示。Frontend `18 files / 90 tests`、typecheck、production build（1813 modules）通过。 |
| SQLite migration | 仅对新建系统临时 SQLite 执行 `upgrade head`、`current --check-heads` 与 `alembic check`；head 为 `20260726_0005`、`No new upgrade operations detected`，临时根目录已验证删除。未读取、迁移、删除或重建 `backend/ai_agent_lab.db`。 |
| 文档与当前事实 | README 中英文、CHANGELOG、项目概览、架构、Knowledge Base 设计、活动 Plan 与设计/实施记录已同步；88 个 Markdown、60 个实际解析的本地链接/图片、0 读取/解析错误、0 missing。当前完成范围止于 `P3-M2-S3`，未声称解析或 ingestion 完成。 |
| 安全、边界与仓库门禁 | 25 个变更路径全部属于 S1～S3 allowlist；新增行高置信 secret、真实 Provider host、generated/database/upload artifact、`web_fetch` production、later runtime 命中均为 0；`git diff --check` 无发现，暂存路径 0。`HEAD == origin/main == 943c3370119db6299484ab6aceda7e6d47870a25`；`v0.2.0^{}` 与 `v0.2.1^{}` 仍分别为 `0e3f3a66e1322c565f2056696f7e482cedbb5f6c`、`872310b4dc1b78e2a2487303699d68ec8b22f88b`。 |
| Codex self-review | must fix：恢复被无必要改写的 `app.knowledge` ownership docstring，相关集合 `49 passed, 1 warning` 且后端全量复验通过。later Step：S4～S6 parser，S7～S9 cleaner/Chunker/pipeline，Document 查询/删除与文件删除协调。accepted limitation：既知 TestClient warning、suffix-only 类型判断、hard-crash orphan、并发同 hash race、删除 Knowledge Base 暂不清理本地文件。not applicable：本批无 ORM/migration、Qdrant client、Provider、前端、外部 review 或 Plan 4+ 能力。无剩余阻塞项。 |

**结论：** `P3-M2-S1～S3` 与 Batch 4 完成。当前证据支持下一批进入
`P3-M2-S4～S6`；本批没有提前实现解析能力。

本批建议 commit：

```text
feat(knowledge): add controlled document upload
```

### P3-M2-S4～S6 文档 Parser 验收记录（2026-07-26）

| 验收项 | 结果与证据 |
|---|---|
| 范围与设计 | 设计 spec 与实施计划均经确认；本批只新增共享 `ParsedDocument`/`ParsedPage` 契约、安全解析错误、Markdown/TXT/文本层 PDF 三个纯 Parser、`pypdf` 依赖及对应测试/文档。未接入上传、数据库、API 或状态机，未开始 S7～S9。 |
| S4 Markdown | 严格 UTF-8/UTF-8 BOM 解码并保留原始 Markdown；fence-aware 状态机提取 ATX/Setext 标题和反引号/波浪号围栏代码块，代码块内的标题样文本不会误识别，未闭合围栏安全保留到文件尾。 |
| S5 TXT | 确定性支持严格 UTF-8、UTF-8 BOM 与带 BOM 的 UTF-16 LE/BE；不使用 locale、概率检测或替换字符。Codex 自审发现 UTF-32 LE BOM 会命中 UTF-16 前缀，新增 RED 回归后显式拒绝 UTF-32，三类 Parser 聚焦集合为 `16 passed`。 |
| S6 PDF | 使用 `pypdf>=6.0.0,<7.0.0`，本机安装 `6.14.2`；真实本地合成 PDF 验证单页/多页顺序、从 1 开始的页码和混合空白页。全无文本层时返回明确的扫描件/纯图片 PDF 需要 OCR 限制；损坏文件返回不泄露路径或底层诊断的通用错误。 |
| TDD RED / GREEN | Markdown RED 为 parser package 缺失，GREEN `4 passed`；TXT RED 为 `parse_txt` 未导出，Markdown/TXT GREEN `10 passed`；PDF RED 为 `parse_pdf` 未导出，三类初次 GREEN `14 passed`；UTF-32 回归 RED 为 `1 failed, 1 passed`，修复后最终 Parser `16 passed`。Parser 加上传/model/schema 相邻回归 `117 passed, 1 warning`。 |
| 依赖与完整回归 | editable install 成功，`pip check` 为 `No broken requirements found`。Backend `651 passed, 1 warning`，warning 为既知 Starlette TestClient/httpx 弃用提示。Frontend `18 files / 90 tests`、typecheck、production build（1813 modules）通过。 |
| SQLite migration | 仅对新建系统临时 SQLite 执行 `upgrade head`、`current --check-heads` 与 `alembic check`；head 为 `20260726_0005`、`No new upgrade operations detected`，临时目录已验证删除。未读取、迁移、删除或重建 `backend/ai_agent_lab.db`。 |
| 文档与当前事实 | README 中英文、CHANGELOG、架构、Knowledge Base 设计、活动 Plan 与设计/实施记录已同步；90 个 Markdown、69 个实际解析的本地链接/图片、0 读取错误、0 missing。当前完成范围止于 `P3-M2-S6`；上传尚不调用 Parser。 |
| 安全、边界与仓库门禁 | 17 个预期变更路径均属于 S4～S6 allowlist；高置信 secret、真实 Provider host、generated PDF/database/upload artifact、`web_fetch` production、S7+ runtime 命中均为 0；`git diff --check` 无发现、暂存路径 0。`HEAD == origin/main == 66955fc9607fd4757e279eab01fae8fdea87b00d`；`v0.2.0^{}` 与 `v0.2.1^{}` 仍分别为 `0e3f3a66e1322c565f2056696f7e482cedbb5f6c`、`872310b4dc1b78e2a2487303699d68ec8b22f88b`。 |
| Codex self-review | must fix：UTF-32 LE BOM 被 UTF-16 前缀优先匹配，已按 systematic debugging 与 TDD 修复并复验。later Step：S7 cleaner、S8 Chunker、S9 parser dispatch/状态/错误持久化，Document 查询/删除与文件删除协调。accepted limitation：PDF 只保证文本层提取，不做 OCR/复杂版面/表格/图片；Markdown 只提取当前约定的标题与围栏；保留既知 TestClient warning。not applicable：本批无 ORM/migration/API/frontend/Qdrant client/Provider、外部 review、Advanced RAG/Rerank/Evaluation/Memory/multimodal。无剩余 must-fix。 |

**结论：** `P3-M2-S4～S6` 与 Batch 5 完成。当前证据支持下一批进入
`P3-M2-S7～S9`；本批未提前实现清洗、Chunking 或 ingestion pipeline。

本批建议 commit：

```text
feat(rag): add markdown txt and pdf parsers
```

### P3-M2-S7～S9 文档处理 Pipeline 验收记录（2026-07-26）

| 验收项 | 结果与证据 |
|---|---|
| 范围与设计 | 用户确认方案 A：现有上传请求同步执行 parse/clean/chunk。成功返回 HTTP 201 最终 `parsed/chunked`；预期内容失败返回 HTTP 201 并持久化安全失败状态；存储、数据库和非预期错误继续向上冒泡并回滚。本批未开始 Embedding、Qdrant client、Retriever、前端或 Plan 4+ runtime。 |
| S7 Text Cleaner | 新增纯 `clean_parsed_document`：统一 CRLF/CR、移除受限 C0/C1 与格式字符、折叠空白空行、保留 tab/Markdown 内容，不修改 Parser 输入；Markdown 标题行 metadata 随清洗重映射，PDF 逐页独立清洗并保留页码。RED 为导入缺失，GREEN `4 passed`。 |
| S8 Chunker 与配置 | 新增 `RAG_CHUNK_SIZE=1000`（100～10,000）和 `RAG_CHUNK_OVERLAP=150`（0～2,000 且小于 size）。Chunker 优先窗口后半段段落边界、其次换行、最后硬边界；保证单调推进、顺序 `chunk_index`、Markdown 标题/PDF 页码来源和不跨 PDF 页。`token_count=max(1, ceil(UTF-8 bytes/4))` 仅为确定性估算。Settings RED 6 项失败后 GREEN `22 passed`；Chunker RED 为契约缺失，Cleaner/config/Chunker GREEN `40 passed`。 |
| S9 Pipeline 与状态 | `DocumentIngestionService` 复用受控存储 resolver，按 UUID ownership 与 suffix 校验文件，分发既有 Parser，串联 Cleaner/Chunker 并 flush `DocumentChunk`。解析失败为 `failed/failed`，清洗后为空为 `parsed/failed`，均不创建 chunk；成功为 `parsed/chunked/pending`。route 保持薄，请求 Session 仍是唯一 commit/rollback owner。 |
| 存储与事务边界 | resolver RED `12 failed, 18 passed`，GREEN `30 passed`，覆盖路径 grammar、ownership/type tamper、缺失/目录及 root/KB/final symlink/reparse。额外自审测试证明 resolver 错误不会伪装成内容失败；数据库 commit 失败会同时回滚 Document、chunks 与新提升文件。 |
| TDD 与聚焦回归 | ingestion success RED 为 service 缺失，GREEN `3 passed`；内容失败 RED 为 `3 failed, 3 passed`，精确 catch 后 GREEN。上传集成 RED 为 8 个新断言失败且 24 个既有断言通过，GREEN `32 passed, 1 warning`；完整 M2 聚焦集合 `179 passed, 1 warning`；最终边界/API 集合 `30 passed, 1 warning`。 |
| 完整回归 | `pip check` 为 `No broken requirements found`。Backend `698 passed, 1 warning`；warning 为既知 Starlette TestClient/httpx 弃用提示。Frontend `18 files / 90 tests`、typecheck、production build（1813 modules）通过。 |
| SQLite 与文档 | 仅对新建系统临时 SQLite 执行 `upgrade head`、`current --check-heads` 与 `alembic check`；head 为 `20260726_0005`、`No new upgrade operations detected`，临时目录已验证删除。92 个 Markdown、69 个本地链接/图片、0 读取错误、0 missing。未读取或修改 `backend/ai_agent_lab.db`。 |
| 安全、边界与 Git 门禁 | 27 个变更路径全部命中 S7～S9 allowlist；新增行高置信 secret、真实 Provider host、generated artifact、later runtime 和禁止的 production 能力命中均为 0。`git diff --check` 无发现，暂存路径 0；`HEAD == origin/main == 39c901efb91d0ccdee49bae950b12106edd21a71`；`v0.2.0^{}` / `v0.2.1^{}` 仍为 `0e3f3a66e1322c565f2056696f7e482cedbb5f6c` / `872310b4dc1b78e2a2487303699d68ec8b22f88b`。 |
| Codex self-review | must fix：移除 ingestion 测试跨测试模块辅助类依赖，并补提交失败的 chunk rollback 与 resolver 错误不被内容失败吞掉的断言，修正 README/架构/Knowledge 文档中的 S6 旧事实；均已复验。later Step：M3 Embedding/Vector Store、后续 Document 查询/删除与文件生命周期协调、M4 Retriever/RAG。accepted limitation：同步处理会占用上传请求时延；token 数仅为估算；扫描 PDF 不做 OCR；hard-crash orphan 与既知 TestClient warning 保留。not applicable：本批无 ORM/migration 变化、真实 Provider/Qdrant 调用、前端、Advanced RAG/Rerank/Evaluation/Memory/multimodal 或外部 review。无剩余 must-fix。 |

**结论：** `P3-M2-S7～S9`、Batch 6 与 M2 完成。当前证据支持下一批进入
`P3-M3-S1～S3`；本批未提前实现 M3 或更晚能力。

M2 完成后建议 commit：

```text
feat(rag): add document processing pipeline
```

### Plan 3 M1/M2 整体审核修复记录（2026-08-01）

| 验收项 | 结果与证据 |
|---|---|
| 范围与基线 | 只审核并修复已完成 M1/M2；开始时 `HEAD == origin/main == c9cefc498a746ad39ee47f5726afc959e8db4f9c`，staged 0，既有 tags 未移动。未开始 M3 或 Plan 4+。 |
| 配置与路径 | Qdrant 6333 只绑定 `127.0.0.1`；Settings 保留 storage-root symlink/reparse 证据；stored path 只接受小写 canonical UUID/suffix 和 POSIX 分隔符。 |
| 资源与 metadata | 默认上限为 PDF 500 页、10,000,000 字符、20,000 Markdown 结构、10,000 chunks；Markdown code-block metadata 不重复正文，Cleaner 保留 fence 内空行并重映射行号，heading 限 512。 |
| 数据完整性 | 新 head `20260801_0006` 增加同 KB hash 唯一、KB→Document RESTRICT、RagQuery answer 单列 SET NULL 与复合 NO ACTION；重复历史组 fail-closed。非空 KB 删除为安全 409，唯一竞争规范化为既有 duplicate 409。 |
| TDD 与聚焦回归 | Task GREEN 依次为 `34`、`68`、`27`、`91`、`33`、`58` 项；最终聚焦集合 `208 passed, 1 warning`。 |
| 全量与依赖 | Backend `735 passed, 1 warning`；`pip check` 为 `No broken requirements found.`；Frontend typecheck、`18 files / 90 tests`、production build `1813 modules` 通过。 |
| SQLite 与文档 | 只对新建系统临时 SQLite 完成 upgrade/current/check/downgrade/re-upgrade，head `20260801_0006`，临时目录已验证删除。95 个 Markdown、69 个本地链接/图片、0 missing。未读取或修改 `backend/ai_agent_lab.db`。 |
| Compose 与边界 | `docker compose config --quiet` 通过；本机 daemon pipe 不可用，当前 health 明确为未复核。高置信 token、unexpected private-key marker、`web_fetch` runtime、later-Plan runtime、tracked artifact 均为 0；staged 0。 |
| Codex self-review | must fix：增强原本会伪通过的路径测试、修复布尔行号重映射、同步陈旧文档，均已复验。later Step：M3 Embedding/Vector Store、Document 删除/文件生命周期、Retriever/RAG/UI。accepted limitation：同步处理、特权 TOCTOU、hard-crash orphan、无新 Docker health、扫描 PDF 无 OCR、既知 warning。not applicable：PostgreSQL 迁移、前端截图、真实 Provider/网络、外部 review。无剩余 must-fix。 |

**结论：** M1/M2 已重新封板。用户手动提交本批后，可以进入
`P3-M3-S1～S3`；本批未提前实现 M3。

建议 commit：

```text
fix(rag): harden plan 3 m1 m2 boundaries
```

---

## 5. Phase 3｜M3 Embedding 与 Vector Store

阶段目标：

```text
建立 Embedding Provider 抽象、OpenAI-compatible Embedding Provider、Qdrant Vector Store，并完成文档入库 Pipeline。
```

阶段验收：

```text
1. Embedding Provider 可替换
2. OpenAI-compatible Embedding Provider 可配置模型和维度
3. Qdrant collection 可创建和检查
4. document_chunks 可以写入 Qdrant
5. Qdrant payload 包含 knowledge_base_id、document_id、chunk_id、metadata
6. 文档入库 Pipeline 从上传文件走到向量写入
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M3-S1 | 设计 EmbeddingProvider 抽象 | Codex | `providers/embedding/base.py` | mock provider 测试通过 | Claude Code 可审 |
| P3-M3-S2 | 定义 EmbeddingResult 和 batch embed 接口 | Codex | embedding schema / dataclass | 批量输入返回向量和 token usage | Codex |
| P3-M3-S3 | 实现 Embedding Provider Registry | Codex | `providers/embedding/registry.py` | 可按配置选择 provider | Codex |
| P3-M3-S4 | 实现 OpenAI-compatible Embedding Provider | Codex | `openai_compatible_embedding.py` | mock HTTP 或测试替身验证请求和响应解析 | Codex |
| P3-M3-S5 | 增加 embedding 配置和错误处理 | Codex | config、provider 初始化逻辑 | 缺少 key 或模型维度不匹配时返回可读错误 | Codex |
| P3-M3-S6 | 补 Embedding Provider 文档 | Codex | `docs/21-embedding-provider.md` | 文档说明配置、模型、维度、成本注意事项 | Codex |
| P3-M3-S7 | 设计 VectorStore 抽象 | Codex | `vectorstores/base.py` | mock vector store 测试通过 | Claude Code 可审 |
| P3-M3-S8 | 实现 Qdrant Vector Store | Codex | `vectorstores/qdrant_store.py` | collection 创建、upsert、search 测试通过 | Codex |
| P3-M3-S9 | 定义 Qdrant payload 规范 | Codex | payload builder | payload 包含 Plan 4 所需字段 | Codex |
| P3-M3-S10 | 实现文档入库 Pipeline | Codex | `ingestion_pipeline.py` | 上传文档后完成 parse、chunk、embed、upsert | Codex |
| P3-M3-S11 | 持久化 chunk vector_id 和 ingest 状态 | Codex | chunk 更新逻辑 | 数据库 chunk 记录关联 Qdrant point id | Codex |
| P3-M3-S12 | 完成 M3 review 和入库文档 | Codex | `docs/22-document-ingestion-pipeline.md` | 端到端入库测试通过 | Codex + Claude review |

M3 完成后建议 commit：

```text
feat(rag): add embedding provider vector store and ingestion pipeline
```

---

## 6. Phase 4｜M4 Retriever 与 Naive RAG API

阶段目标：

```text
实现 Top-K Retriever、RAG Prompt、RAG Query API、RAG Chat API，并把知识库检索注册成 Tool。
```

阶段验收：

```text
1. Retriever 可以按 query 检索相关 chunk
2. RAG Prompt 独立封装，便于 PLAN4 优化
3. RAG Query API 返回 answer、sources、retrieval metadata
4. RAG Chat API 可以复用会话系统
5. rag_queries 或等价查询记录可用
6. search_knowledge_base 工具可以被 Plan 2 的 Agent Loop 调用
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M4-S1 | 实现 Retriever | Codex | `retriever.py` | 给定 query 返回 Top-K RetrievalResult | Claude Code 可审 |
| P3-M4-S2 | 实现检索 metadata 和来源结构 | Codex | `RetrievalResult` schema | 返回 chunk_id、document_id、score、content、metadata | Codex |
| P3-M4-S3 | 补 Retriever 测试 | Codex | retriever tests | mock vector store 检索测试通过 | Codex |
| P3-M4-S4 | 实现 RAG Prompt 模板 | Codex | `prompts/rag_prompt.md` 或 prompt builder | Prompt 包含问题、上下文、来源约束 | Codex |
| P3-M4-S5 | 实现 RAG Query Service 和 API | Codex | `rag_service.py`、`api/v1/rag.py` | API 返回 answer、sources、metadata | Codex |
| P3-M4-S6 | 实现 RAG Chat API | Codex | rag chat endpoint | 能把 RAG 回答写入会话历史 | Codex |
| P3-M4-S7 | 实现 rag_queries 记录 | Codex | 查询记录写入逻辑 | 记录 query、knowledge_base_id、top_k、source ids、latency | Codex |
| P3-M4-S8 | 注册 search_knowledge_base 工具 | Codex | `tools/builtin/search_knowledge_base.py` | Agent 可调用 RAG Tool 返回检索结果 | Codex + Claude review |

M4 完成后建议 commit：

```text
feat(rag): add naive rag query chat and tool integration
```

---

## 7. Phase 5｜M5 前端知识库与 RAG Chat

阶段目标：

```text
实现知识库管理页面、文档上传页面、RAG Chat 页面和来源片段展示，让 Plan 3 成为可展示的 MVP。
```

阶段验收：

```text
1. 前端可以创建和查看知识库
2. 前端可以上传 Markdown / TXT / PDF
3. 前端可以查看文档解析 / 入库状态
4. 前端可以基于知识库提问
5. 前端可以展示回答和来源片段
6. 典型验收场景可以完整跑通
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M5-S1 | 创建前端 Knowledge Base API 封装和类型 | Cursor | `frontend/src/api/knowledge.ts`、types | TypeScript 检查通过 | Codex |
| P3-M5-S2 | 实现知识库列表和创建页面 | Cursor | `KnowledgeBasePage.tsx` | 可创建、查看知识库 | Codex |
| P3-M5-S3 | 实现文档上传和状态展示 | Cursor | Document upload component | 可上传文件并显示 parse / ingest 状态 | Codex |
| P3-M5-S4 | 创建前端 RAG API 封装和 store | Cursor | `api/rag.ts`、rag store | TypeScript 检查通过 | Codex |
| P3-M5-S5 | 实现 RAG Chat 页面 | Cursor | `RagChatPage.tsx` | 可选择知识库并提问 | Codex |
| P3-M5-S6 | 实现来源片段展示组件 | Cursor | `SourceCitationList.tsx`、source cards | 展示文档名、chunk 片段、score、metadata | Codex review |

M5 完成后建议 commit：

```text
feat(frontend): add knowledge base and rag chat pages
```

---

## 8. Phase 6｜M6 测试、文档与封版

阶段目标：

```text
补齐 Plan 3 的测试、文档、截图、CHANGELOG 和 v0.3.0 tag，让它成为第一个真正可展示的 AI 应用 MVP。
```

阶段验收：

```text
1. Knowledge Base / Document / Chunk / RAG API 有核心测试
2. Parser / Cleaner / Chunker / Embedding / Vector Store / Retriever 有测试
3. 前端知识库和 RAG Chat 通过手动或 smoke 验证
4. README 和 docs 说明上传、入库、RAG 问答、限制
5. CHANGELOG 记录 v0.3.0
6. 创建 v0.3.0 tag
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P3-M6-S1 | 补数据模型、Knowledge Base API、Document API 测试 | Codex | 后端测试 | `pytest` 对应测试通过 | Codex |
| P3-M6-S2 | 补 Parser、Cleaner、Chunker 测试 | Codex | 文档处理测试 | Markdown / TXT / PDF 文本型样例通过 | Codex |
| P3-M6-S3 | 补 Embedding、Vector Store、Ingestion、Retriever 测试 | Codex | RAG pipeline 测试 | mock embedding + test Qdrant 或 mock vector store 通过 | Codex |
| P3-M6-S4 | 补 RAG Query / Chat / Tool 测试 | Codex | RAG API 和 Tool 测试 | 检索、回答、来源、rag_queries 记录通过 | Codex |
| P3-M6-S5 | 补前端检查和 Demo 验证 | Cursor + Codex | 前端 build、截图、手动验证记录 | 上传文档、提问、展示来源可跑通 | Codex |
| P3-M6-S6 | 更新 README、docs、CHANGELOG、创建 v0.3.0 tag | Codex + Claude Code | 文档、截图、tag、桥接检查表 | 全量测试通过，tag 存在 | Codex + Claude final review |

M6 完成后建议 commit：

```text
chore: release v0.3.0 naive rag
```

---

## 9. 每次执行 1～3 步的标准流程

每次让 Codex / Cursor 执行时，建议按这个模板下发：

```text
当前执行范围：P3-Mx-Sy ～ P3-Mx-Sz
必须遵守：只做这些 Step，不提前做 Hybrid Search、Rerank、Evaluation、Memory 或多模态
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
2. 是否引入超出 Plan 3 的 Advanced RAG 能力
3. 是否破坏 Plan 1 Chat 或 Plan 2 Tool Calling
4. RAG 模块是否保持 Provider / Vector Store / Retriever 可替换
5. metadata、source、vector_id 是否保留 Plan 4 扩展点
6. 是否有测试或手动验证证据
7. 是否同步 README / docs / env example
8. 是否适合进入下一批次
```

---

## 10. Claude Code Review 节点

Claude Code 不需要每个 Step 都参与，建议在这些节点使用：

| 节点 | 审核重点 | 输入材料 |
|---|---|---|
| M1 结束 | 数据模型是否能支撑 Plan 4 的 Trace / Advanced RAG | diff、ORM、schema、API、测试结果 |
| M3 结束 | Embedding / Vector Store / Ingestion 抽象是否稳定 | diff、provider、vector store、pipeline、payload 规范、测试结果 |
| M4 结束 | Retriever / RAG API / Tool 集成是否可扩展 | diff、retriever、prompt、RAG API、search_knowledge_base、测试结果 |
| M6 封版前 | v0.3.0 是否能作为 Plan 4 的工程化 RAG 底座 | 全量 diff、README、测试结果、CHANGELOG、桥接检查 |

Claude Code 审核后，Codex 负责：

```text
1. 判断哪些意见必须修
2. 拆成 1～3 个修复 Step
3. 修复后重新跑测试
4. 更新文档和 changelog
```

---

## 11. Plan 3 最终验收清单

| 验收项 | 状态 | 证据 |
|---|---|---|
| Qdrant 可启动 | implemented | Qdrant 1.15.4 容器运行、重启次数为 0；`/healthz` 返回 HTTP 200 |
| Knowledge Base 数据模型完成 | implemented | `KnowledgeBase` ORM/schema、revision `20260726_0005` 与补丁 `20260801_0006`、模型/迁移测试 |
| Document 数据模型完成 | implemented | `Document` ORM/schema、状态/hash/metadata 与同 KB hash 唯一约束、模型/迁移测试 |
| DocumentChunk 数据模型完成 | implemented | `DocumentChunk` ORM/schema、复合 ownership 外键、模型/迁移测试 |
| 可以创建知识库 | implemented | Knowledge Base service/API CRUD、OpenAPI 与临时 SQLite API 测试 |
| 可以上传 Markdown | implemented | M2 上传 API 与同步 Pipeline 验收记录 |
| 可以上传 TXT | implemented | M2 上传 API 与同步 Pipeline 验收记录 |
| 可以上传文本型 PDF | implemented | M2 上传 API 与文本层 PDF Parser 验收记录 |
| 可以解析文档 | implemented | Markdown/TXT/PDF parser 测试与资源上限回归 |
| 可以清洗文本 | implemented | fence-aware cleaner 与结构行号重映射测试 |
| 可以切分 Chunk | implemented | chunker、放大上限、heading 边界与 ingestion 测试 |
| 可以调用 Embedding Provider | pending | provider 测试 |
| 可以写入 Qdrant | pending | vector store 测试 |
| 可以基于 query 检索 Chunk | pending | retriever 测试 |
| 可以基于检索结果生成回答 | pending | RAG API 测试 |
| 前端可以上传文档 | pending | 页面截图 |
| 前端可以查看文档状态 | pending | 页面截图 |
| 前端可以进行 RAG Chat | pending | 页面截图 |
| 前端可以展示来源片段 | pending | 页面截图 |
| search_knowledge_base 工具可用 | pending | Agent Tool 测试 |
| README 已更新 | implemented | 中英文 README 的 M1/M2 当前契约与限制 |
| docs 已更新 | implemented | Architecture、Knowledge Base 设计和 M1/M2 审计记录 |
| 已创建 v0.3.0 tag | pending | `git tag --list` 输出 |

---

## 12. Plan 3 到 Plan 4 的桥接检查

只有下面 5 项都满足，才建议进入 Plan 4：

| 桥接项 | 状态 | 说明 |
|---|---|---|
| `search_knowledge_base` 工具可用 | pending | 后续 Agent 和 Trace 能统一观察 RAG 调用 |
| `rag_queries` 或等价查询记录可用 | pending | Plan 4 可以扩展为检索 Trace |
| `document_chunks` 至少包含 document_id、chunk_index、content、metadata、vector_id | pending | Parent-Child / metadata filter / rerank 都依赖这些字段 |
| RAG Query API 返回 answer、sources、retrieval metadata | pending | Evaluation 和 Trace 需要统一结果结构 |
| Qdrant payload 中保留 knowledge_base_id、document_id、chunk_id | pending | Plan 4 的过滤、来源展示、检索记录都依赖 payload |

---

## 13. 推荐文件位置

执行过程中建议把相关产物放在这些位置：

| 类型 | 路径 |
|---|---|
| Knowledge Base API | `backend/app/api/v1/knowledge_bases.py` |
| Document API | `backend/app/api/v1/documents.py` |
| RAG API | `backend/app/api/v1/rag.py` |
| 数据模型 | `backend/app/models/knowledge_base.py`、`document.py`、`document_chunk.py`、`rag_query.py` |
| 文档处理 | `backend/app/rag/parsers/`、`text_cleaner.py`、`chunker.py` |
| Embedding Provider | `backend/app/providers/embedding/` |
| Vector Store | `backend/app/rag/vectorstores/` |
| Ingestion Pipeline | `backend/app/rag/ingestion_pipeline.py` |
| Retriever | `backend/app/rag/retriever.py` |
| RAG Prompt | `backend/app/prompts/rag_prompt.md` 或 `backend/app/rag/prompt_builder.py` |
| RAG Tool | `backend/app/tools/builtin/search_knowledge_base.py` |
| 后端测试 | `backend/tests/rag/`、`backend/tests/knowledge/` |
| 前端知识库页面 | `frontend/src/pages/KnowledgeBasePage.tsx` |
| 前端 RAG 页面 | `frontend/src/pages/RagChatPage.tsx` |
| 前端来源组件 | `frontend/src/components/rag/` |
| 项目文档 | `docs/20-knowledge-base-design.md`、`docs/21-embedding-provider.md`、`docs/22-document-ingestion-pipeline.md`、`docs/23-naive-rag.md` |
| 截图 | `docs/assets/plan3/` |

---

## 14. 执行建议

Plan 3 的重点不是追求“最强 RAG”，而是把 Naive RAG 的工程链路做完整、可观察、可扩展。

推荐实际推进方式：

```text
先做 Knowledge Base 和文档数据模型
再做上传、解析、清洗、Chunking
再做 Embedding 和 Qdrant 入库
再做 Retriever、RAG Prompt 和 RAG API
再接前端页面和 search_knowledge_base 工具
最后补测试、文档、截图和 v0.3.0 封版
```

不要在 Plan 3 阶段提前优化检索策略。

Plan 3 做稳之后，Plan 4 才能自然地在同一套 Retriever、Vector Store、Prompt、RAG Query 记录上增加 Trace、Hybrid Search、Rerank 和 Evaluation。
