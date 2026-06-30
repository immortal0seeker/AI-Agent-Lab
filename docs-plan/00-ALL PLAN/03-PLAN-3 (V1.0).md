# Plan 3｜知识库系统：Document Ingestion + Naive RAG

## 0. 子计划定位

Plan 3 对应项目总路线中的：

```text
Phase 3：知识库 + Naive RAG
```

Plan 3 的前置条件是：

```text
Plan 1 已完成
版本：v0.1.0
成果：基础 Chat 平台可运行

Plan 2 已完成
版本：v0.2.0
成果：Tool Calling + 简单 Agent Loop 可运行
```

也就是说，项目已经具备：

- FastAPI 后端
    
- React WebUI
    
- SQLite 会话存储
    
- LLM Provider 抽象
    
- Streaming Chat
    
- 会话历史
    
- Token / Cost / Latency 统计
    
- Tool Registry
    
- read_file 工具
    
- list_dir 工具
    
- Simple Agent Loop
    
- Tool Call 记录
    
- 前端 Tool Call 展示
    
- 基础工具安全边界
    

Plan 3 不重写 Chat，也不重写 Agent Loop。

Plan 3 的目标是在现有系统上增加：

> 文档上传、文档解析、Chunking、Embedding、Qdrant 向量存储、Vector Search、Naive RAG 问答和来源展示。

---

## 1. Plan 3 核心目标

Plan 3 的目标是：

> 让 AI Agent Lab 第一次具备“知识库问答能力”。

完成 Plan 3 后，系统应该支持：

```text
用户上传文档
    ↓
后端保存文档
    ↓
解析文档内容
    ↓
切分 Chunk
    ↓
调用 Embedding Provider
    ↓
写入 Qdrant
    ↓
用户基于文档提问
    ↓
系统检索相关 Chunk
    ↓
将 Chunk 注入 Prompt
    ↓
LLM 生成回答
    ↓
前端展示回答和来源片段
```

典型验收场景：

```text
用户上传 docs/01-architecture.md

用户提问：
AI Agent Lab 的总体架构是什么？

系统：
1. 检索相关 Chunk
2. 将 Chunk 注入 RAG Prompt
3. 生成回答
4. 展示命中的文档片段和来源
```

---

## 2. Plan 3 不做什么

为了保证 Plan 3 稳定完成，暂时不做以下内容：

|暂不做|原因|
|---|---|
|Hybrid Search|放到 Plan 4|
|Parent-Child Retrieval|放到 Plan 4|
|Rerank|放到 Plan 4|
|Query Rewrite|放到 Plan 4|
|HyDE|放到 Plan 4 或更后|
|GraphRAG|后期研究，不进 MVP|
|Agentic RAG|放到 Plan 5 之后|
|多知识库复杂权限|后期做|
|Word / Excel / PPT 复杂解析|先后置|
|OCR 文档解析|放到 Plan 6|
|图片知识库|放到 Plan 6|
|视频 / 音频知识库|放到 Plan 6|
|自动评测 RAG|放到 Plan 4|

Plan 3 只做：

> Naive RAG 的完整闭环。

---

## 3. Plan 3 版本目标

|项目|内容|
|---|---|
|子计划名称|Plan 3：知识库系统|
|对应 Phase|Phase 3|
|起始版本|v0.2.0|
|目标版本|v0.3.0|
|核心能力|文档上传 + Naive RAG|
|预计时间|80～120 小时|
|难度|中等偏高|
|项目价值|第一个真正具备作品集价值的 AI 应用 MVP|

---

## 4. Plan 3 技术重点

Plan 3 重点学习和实现：

- 文件上传
    
- 文件存储
    
- 文档解析
    
- Markdown / TXT / PDF 解析
    
- Text Cleaning
    
- Chunking
    
- Token 估算
    
- Embedding Provider
    
- Qdrant
    
- Collection / Point / Payload
    
- Vector Search
    
- RAG Prompt
    
- Source Citation
    
- RAG Chat API
    
- 前端知识库页面
    
- 前端来源片段展示
    

---

## 5. Plan 3 文档类型范围

Plan 3 只支持三类文档：

|文档类型|是否支持|说明|
|---|---|---|
|Markdown|支持|优先支持，最适合技术文档|
|TXT|支持|简单文本|
|PDF|支持|只做文本提取，不做 OCR|

暂不支持：

```text
Word
Excel
CSV
PPT
HTML
网页
图片
截图
音频
视频
Obsidian Vault 批量导入
GitHub Repo 批量导入
```

---

## 6. Plan 3 推荐目录结构调整

在 Plan 2 基础上，新增以下模块：

```text
backend/app/
├── rag/
│   ├── document_loader.py
│   ├── parser.py
│   ├── cleaner.py
│   ├── chunker.py
│   ├── embedding_service.py
│   ├── vector_store.py
│   ├── retriever.py
│   ├── rag_prompt.py
│   └── rag_service.py
│
├── providers/
│   ├── embedding/
│   │   ├── base.py
│   │   ├── openai_compatible.py
│   │   └── registry.py
│   └── vectorstore/
│       ├── base.py
│       └── qdrant_store.py
│
├── models/
│   ├── knowledge_base.py
│   ├── document.py
│   └── document_chunk.py
│
├── schemas/
│   ├── knowledge_base.py
│   ├── document.py
│   └── rag.py
│
└── api/v1/
    ├── knowledge_bases.py
    ├── documents.py
    └── rag.py
```

前端新增：

```text
frontend/src/
├── pages/
│   ├── KnowledgeBasePage.tsx
│   └── RagChatPage.tsx
│
├── components/
│   └── rag/
│       ├── FileUploadPanel.tsx
│       ├── KnowledgeBaseList.tsx
│       ├── DocumentList.tsx
│       ├── ChunkPreview.tsx
│       ├── RagSourceCard.tsx
│       └── RagAnswerPanel.tsx
│
├── api/
│   ├── knowledgeBases.ts
│   ├── documents.ts
│   └── rag.ts
│
└── types/
    ├── knowledgeBase.ts
    ├── document.ts
    └── rag.ts
```

---

## 7. Plan 3 数据库设计

### 7.1 knowledge_bases

用于管理知识库。

```sql
knowledge_bases
- id
- name
- description
- embedding_provider
- embedding_model
- vector_store
- vector_collection_name
- created_at
- updated_at
```

---

### 7.2 documents

用于记录上传文档。

```sql
documents
- id
- knowledge_base_id
- filename
- original_filename
- file_type
- file_path
- file_size
- file_hash
- parse_status
- chunk_status
- embedding_status
- error_message
- created_at
- updated_at
```

状态建议：

```text
uploaded
parsing
parsed
chunking
chunked
embedding
ready
failed
```

---

### 7.3 document_chunks

用于记录文档切片。

```sql
document_chunks
- id
- document_id
- knowledge_base_id
- chunk_index
- content
- token_count
- char_count
- heading
- page_number
- metadata_json
- vector_id
- created_at
```

---

### 7.4 rag_queries

可选，用于记录 RAG 查询。

```sql
rag_queries
- id
- conversation_id
- knowledge_base_id
- query
- retrieved_chunks_json
- answer_message_id
- latency_ms
- created_at
```

Plan 3 可以先做简化版，如果时间紧，rag_queries 可以放到 Plan 4 的 Trace 系统一起补。

---

## 8. Plan 3 核心接口设计

### 8.1 Knowledge Base API

```text
POST /api/v1/knowledge-bases
GET /api/v1/knowledge-bases
GET /api/v1/knowledge-bases/{kb_id}
DELETE /api/v1/knowledge-bases/{kb_id}
```

---

### 8.2 Document API

```text
POST /api/v1/knowledge-bases/{kb_id}/documents
GET /api/v1/knowledge-bases/{kb_id}/documents
GET /api/v1/documents/{document_id}
GET /api/v1/documents/{document_id}/chunks
DELETE /api/v1/documents/{document_id}
```

---

### 8.3 RAG API

```text
POST /api/v1/rag/query
POST /api/v1/rag/chat
```

`rag/query` 只返回检索结果。

`rag/chat` 返回基于检索结果生成的回答。

---

## 9. Plan 3 核心数据结构

### 9.1 ParsedDocument

```python
class ParsedDocument:
    document_id: str
    text: str
    metadata: dict
    pages: list[dict] | None
```

---

### 9.2 DocumentChunk

```python
class DocumentChunk:
    id: str
    document_id: str
    knowledge_base_id: str
    chunk_index: int
    content: str
    token_count: int
    metadata: dict
```

---

### 9.3 RetrievalResult

```python
class RetrievalResult:
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict
```

---

### 9.4 RagAnswer

```python
class RagAnswer:
    answer: str
    sources: list[RetrievalResult]
    model: str
    usage: dict | None
```

---

## 10. Plan 3 详细步骤

## Step 1：确认 Plan 2 封版状态

### 要做什么

检查 v0.2.0 是否稳定。

### 检查清单

```text
[ ] 基础 Chat 可用
[ ] Streaming 可用
[ ] LLM Provider 可用
[ ] Tool Registry 可用
[ ] read_file 可用
[ ] list_dir 可用
[ ] Simple Agent Loop 可用
[ ] Tool Call 记录可用
[ ] 前端 Tool Call 展示可用
[ ] 已创建 tag v0.2.0
```

### 完成标准

```text
Plan 3 不重写 Plan 2，只在其上新增知识库模块。
```

### 预计时间

2～4 小时

---

## Step 2：启动 Qdrant 服务

### 要做什么

在 docker-compose 中加入 Qdrant。

### 任务清单

```text
[ ] 更新 docker-compose.yml
[ ] 增加 qdrant 服务
[ ] 配置 volume
[ ] 配置端口 6333
[ ] 后端 .env 增加 QDRANT_URL
[ ] 测试 Qdrant 是否可访问
```

### 为什么做

Qdrant 是 Plan 3 的向量数据库。

### 完成标准

```text
docker compose up -d qdrant 后，Qdrant 正常运行。
```

### 预计时间

3～5 小时

### 建议 commit

```text
chore: add qdrant service
```

---

## Step 3：设计 Knowledge Base 数据模型

### 要做什么

创建知识库、文档、Chunk 的数据库模型。

### 任务清单

```text
[ ] 创建 KnowledgeBase ORM
[ ] 创建 Document ORM
[ ] 创建 DocumentChunk ORM
[ ] 创建 Alembic migration
[ ] 写基础数据库测试
```

### 为什么做

知识库系统必须有结构化元数据，不能只把向量丢进 Qdrant。

### 完成标准

```text
可以创建知识库、插入文档记录、插入 Chunk 记录。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(rag): add knowledge base document and chunk models
```

---

## Step 4：实现 Knowledge Base API

### 要做什么

实现知识库管理接口。

### 任务清单

```text
[ ] 创建 schemas/knowledge_base.py
[ ] 创建 api/v1/knowledge_bases.py
[ ] 创建 knowledge_base_service.py
[ ] 实现创建知识库
[ ] 实现知识库列表
[ ] 实现知识库详情
[ ] 实现删除知识库
```

### 完成标准

```text
Swagger 可以创建和查看知识库。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(rag): add knowledge base api
```

---

## Step 5：实现文件上传

### 要做什么

支持上传 Markdown / TXT / PDF。

### 任务清单

```text
[ ] 创建 uploads 目录
[ ] 设计文件保存路径
[ ] 支持 multipart file upload
[ ] 校验文件类型
[ ] 限制文件大小
[ ] 计算 file_hash
[ ] 保存 document 记录
[ ] 返回 document_id
```

### 文件限制建议

```text
Plan 3 初版：
单文件最大 20MB
单个知识库最多 50 个文档
只允许 .md / .txt / .pdf
```

### 完成标准

```text
用户可以上传文档，后端生成 document 记录。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(rag): add document upload
```

---

## Step 6：实现文档解析

### 要做什么

解析 Markdown / TXT / PDF 文本。

### 任务清单

```text
[ ] 创建 rag/parser.py
[ ] 实现 parse_markdown()
[ ] 实现 parse_txt()
[ ] 实现 parse_pdf()
[ ] 提取基础 metadata
[ ] 解析失败时记录 error_message
```

### PDF 说明

Plan 3 只做文本层 PDF 解析：

```text
支持可复制文本的 PDF
不支持扫描版 PDF OCR
不支持复杂表格结构还原
不支持图片理解
```

### 完成标准

```text
上传文档后，可以提取出文本内容。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(rag): add markdown txt pdf parser
```

---

## Step 7：实现文本清洗

### 要做什么

对解析文本做基础清洗。

### 任务清单

```text
[ ] 去除过多空行
[ ] 统一换行符
[ ] 清除不可见字符
[ ] 保留 Markdown 标题
[ ] PDF 文本做简单页码 metadata
[ ] 清洗结果可调试查看
```

### 为什么做

脏文本会直接影响 Chunking 和检索质量。

### 完成标准

```text
清洗后的文本结构基本可读。
```

### 预计时间

4～8 小时

### 建议 commit

```text
feat(rag): add document text cleaner
```

---

## Step 8：实现 Chunking

### 要做什么

将文档切成可检索的 Chunk。

### 初版策略

```text
chunk_size: 800～1200 字符
chunk_overlap: 100～200 字符
保留 heading
保留 page_number
保留 document_id
保留 chunk_index
```

### 任务清单

```text
[ ] 创建 rag/chunker.py
[ ] 实现按字符切分
[ ] 尽量按段落边界切分
[ ] 保留 chunk_index
[ ] 估算 token_count
[ ] 保存 document_chunks
```

### 完成标准

```text
一个文档可以被切分成多个 Chunk，并写入数据库。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(rag): add naive document chunker
```

---

## Step 9：实现 Embedding Provider 抽象

### 要做什么

定义统一 Embedding 接口。

### 任务清单

```text
[ ] 创建 providers/embedding/base.py
[ ] 定义 EmbeddingProvider
[ ] 定义 embed_texts()
[ ] 定义 embed_query()
[ ] 定义 EmbeddingResult
[ ] 支持 batch embedding
```

### 为什么做

Embedding 模型后续可能切换 OpenAI、Qwen、BGE、Jina，本阶段就要避免绑定单一厂商。

### 完成标准

```text
业务代码不直接依赖某一家 embedding API。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(embedding): add embedding provider abstraction
```

---

## Step 10：实现 OpenAI-Compatible Embedding Provider

### 要做什么

实现可调用真实 embedding 模型的 Provider。

### 任务清单

```text
[ ] 支持 base_url
[ ] 支持 api_key
[ ] 支持 model
[ ] 实现 embed_texts()
[ ] 实现 embed_query()
[ ] 支持批量请求
[ ] 记录 embedding model
[ ] 处理 API 错误
```

### 可选模型

```text
OpenAI embedding
Qwen embedding
BGE API
Jina Embeddings
OpenRouter 或其他兼容服务
```

### 完成标准

```text
可以把 Chunk 文本转成向量。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(embedding): implement openai compatible embedding provider
```

---

## Step 11：实现 Qdrant Vector Store

### 要做什么

封装 Qdrant 操作。

### 任务清单

```text
[ ] 创建 providers/vectorstore/base.py
[ ] 创建 providers/vectorstore/qdrant_store.py
[ ] 创建 collection
[ ] upsert vectors
[ ] search vectors
[ ] delete document vectors
[ ] 保存 payload
```

### Payload 建议

```json
{
  "knowledge_base_id": "kb_xxx",
  "document_id": "doc_xxx",
  "chunk_id": "chunk_xxx",
  "filename": "README.md",
  "chunk_index": 0,
  "heading": "项目介绍",
  "page_number": null
}
```

### 完成标准

```text
Chunk 向量可以写入 Qdrant，并能按 query 检索回来。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(vectorstore): add qdrant vector store
```

---

## Step 12：实现文档入库 Pipeline

### 要做什么

串联上传、解析、清洗、切分、Embedding、写入 Qdrant。

### Pipeline

```text
upload document
    ↓
parse document
    ↓
clean text
    ↓
split chunks
    ↓
embed chunks
    ↓
upsert to qdrant
    ↓
mark document ready
```

### 任务清单

```text
[ ] 创建 document_ingestion_service.py
[ ] 串联 parser / cleaner / chunker
[ ] 调用 embedding provider
[ ] 调用 qdrant store
[ ] 更新 document 状态
[ ] 失败时记录错误
```

### 初版说明

```text
Plan 3 初版可以同步执行，不必急着上 Celery / RQ。
等文档较大或任务较慢时，再放到 Plan 4 或后续 Worker。
```

### 完成标准

```text
上传文档后，可以完成入库，并变成 ready 状态。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(rag): add document ingestion pipeline
```

---

## Step 13：实现 Retriever

### 要做什么

实现基础向量检索。

### 任务清单

```text
[ ] 创建 rag/retriever.py
[ ] 输入 query
[ ] query embedding
[ ] Qdrant top_k search
[ ] 返回 RetrievalResult
[ ] 支持 knowledge_base_id 过滤
[ ] 支持 top_k 参数
```

### 初版参数

```text
top_k = 5
score_threshold = 可选
```

### 完成标准

```text
输入问题后，可以检索出相关 Chunk。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(rag): add naive vector retriever
```

---

## Step 14：实现 RAG Prompt

### 要做什么

将检索结果注入 Prompt。

### Prompt 结构

```text
你是 AI Agent Lab 的知识库问答助手。

请基于给定资料回答用户问题。
如果资料中没有答案，请明确说明“资料中没有找到相关信息”。
不要编造来源。

【资料片段】
[1] 文件：xxx.md
内容：...

[2] 文件：yyy.pdf，第 3 页
内容：...

【用户问题】
xxx
```

### 任务清单

```text
[ ] 创建 rag/rag_prompt.py
[ ] 格式化 sources
[ ] 限制注入上下文长度
[ ] 保留 source index
[ ] 构造 messages
```

### 完成标准

```text
LLM 回答时能基于检索片段生成结果。
```

### 预计时间

5～8 小时

### 建议 commit

```text
feat(rag): add rag prompt builder
```

---

## Step 15：实现 RAG Query API

### 要做什么

实现只检索、不生成回答的接口。

### 接口

```text
POST /api/v1/rag/query
```

请求：

```json
{
  "knowledge_base_id": "kb_xxx",
  "query": "AI Agent Lab 的目标是什么？",
  "top_k": 5
}
```

返回：

```json
{
  "results": [
    {
      "chunk_id": "chunk_xxx",
      "document_id": "doc_xxx",
      "content": "...",
      "score": 0.82,
      "metadata": {}
    }
  ]
}
```

### 为什么做

便于调试检索质量。

### 完成标准

```text
Swagger 可以直接测试检索效果。
```

### 预计时间

5～8 小时

### 建议 commit

```text
feat(rag): add rag query api
```

---

## Step 16：实现 RAG Chat API

### 要做什么

实现完整 RAG 问答接口。

### 接口

```text
POST /api/v1/rag/chat
```

请求：

```json
{
  "conversation_id": "conv_xxx",
  "knowledge_base_id": "kb_xxx",
  "provider": "deepseek",
  "model": "deepseek-chat",
  "query": "这个项目的总体架构是什么？",
  "top_k": 5
}
```

流程：

```text
保存用户问题
    ↓
检索 Chunk
    ↓
构造 RAG Prompt
    ↓
调用 LLM
    ↓
保存 assistant 回答
    ↓
返回 answer + sources
```

### 完成标准

```text
用户可以基于知识库进行问答。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(rag): add rag chat api
```

---

## Step 17：把 RAG 作为工具注册到 Tool Registry

### 要做什么

将知识库检索作为一个工具：

```text
search_knowledge_base
```

### 参数

```json
{
  "knowledge_base_id": "kb_xxx",
  "query": "xxx",
  "top_k": 5
}
```

### 为什么做

这样 Plan 3 可以和 Plan 2 流畅衔接。

Chat 模式可以直接调用 RAG Chat。

Agent 模式则可以通过工具调用：

```text
Agent → search_knowledge_base → LLM 总结
```

### 任务清单

```text
[ ] 创建 tools/builtin/search_knowledge_base.py
[ ] 复用 retriever
[ ] 注册到 Tool Registry
[ ] 限制 top_k
[ ] 返回检索结果摘要
```

### 完成标准

```text
Simple Agent 可以调用 search_knowledge_base 工具。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(rag): expose knowledge base search as tool
```

---

## Step 18：前端知识库页面

### 要做什么

实现基础 Knowledge Base UI。

### 页面功能

```text
[ ] 创建知识库
[ ] 查看知识库列表
[ ] 上传文档
[ ] 查看文档列表
[ ] 查看文档状态
[ ] 查看 Chunk 预览
```

### 组件

```text
KnowledgeBasePage
KnowledgeBaseList
FileUploadPanel
DocumentList
ChunkPreview
```

### 完成标准

```text
用户可以通过前端完成文档上传和入库。
```

### 预计时间

12～20 小时

### 建议 commit

```text
feat(frontend): add knowledge base page
```

---

## Step 19：前端 RAG Chat 与来源展示

### 要做什么

在前端展示 RAG 问答结果和来源片段。

### 展示内容

```text
回答内容
命中文档名
Chunk 内容
相似度分数
页码 / 标题 metadata
```

### 组件

```text
RagChatPage
RagSourceCard
RagAnswerPanel
```

### 完成标准

```text
用户提问后，可以看到回答和来源片段。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(frontend): add rag chat and source display
```

---

## Step 20：补充 RAG 测试

### 要做什么

给文档处理和检索写基础测试。

### 测试范围

```text
[ ] Markdown 解析测试
[ ] TXT 解析测试
[ ] PDF 解析测试
[ ] Chunking 测试
[ ] Embedding Provider mock 测试
[ ] Qdrant Store mock 或集成测试
[ ] Retriever 测试
[ ] RAG Prompt 测试
[ ] RAG API 测试
```

### 完成标准

```text
核心 RAG Pipeline 有基础测试。
```

### 预计时间

8～14 小时

### 建议 commit

```text
test(rag): add basic rag pipeline tests
```

---

## Step 21：补充 Plan 3 文档

### 要做什么

写清楚知识库和 Naive RAG 设计。

### 文档建议

```text
docs/10-plan-3-knowledge-base.md
docs/11-document-ingestion.md
docs/12-chunking.md
docs/13-embedding-provider.md
docs/14-qdrant-vector-store.md
docs/15-naive-rag.md
```

### 每篇文档写什么

```text
1. 模块目标
2. 为什么这样设计
3. 核心数据结构
4. API 说明
5. 当前限制
6. 后续如何升级到 Advanced RAG
```

### 完成标准

```text
别人能看懂文档上传、向量化、检索、问答的完整链路。
```

### 预计时间

8～12 小时

### 建议 commit

```text
docs: add plan 3 knowledge base documents
```

---

## Step 22：Plan 3 封版

### 要做什么

发布 v0.3.0。

### 任务清单

```text
[ ] 更新 README
[ ] 更新 CHANGELOG.md
[ ] 截图知识库页面
[ ] 截图 RAG Chat 页面
[ ] 记录当前支持的文档格式
[ ] 记录当前 RAG 限制
[ ] 创建 Git tag：v0.3.0
```

### 完成标准

```text
从 README 启动项目后，可以完成：
1. 创建知识库
2. 上传 Markdown / TXT / PDF
3. 文档入库
4. 基于文档问答
5. 查看来源片段
```

### 建议 commit

```text
chore: release v0.3.0 naive rag
```

---

## 11. Plan 3 最终验收标准

Plan 3 完成后，必须满足：

```text
[ ] Qdrant 可启动
[ ] Knowledge Base 数据模型完成
[ ] Document 数据模型完成
[ ] DocumentChunk 数据模型完成
[ ] 可以创建知识库
[ ] 可以上传 Markdown
[ ] 可以上传 TXT
[ ] 可以上传文本型 PDF
[ ] 可以解析文档
[ ] 可以清洗文本
[ ] 可以切分 Chunk
[ ] 可以调用 Embedding Provider
[ ] 可以写入 Qdrant
[ ] 可以基于 query 检索 Chunk
[ ] 可以基于检索结果生成回答
[ ] 前端可以上传文档
[ ] 前端可以查看文档状态
[ ] 前端可以进行 RAG Chat
[ ] 前端可以展示来源片段
[ ] search_knowledge_base 工具可用
[ ] README 已更新
[ ] docs 已更新
[ ] 已创建 v0.3.0 tag
```

---

## 12. Plan 3 最小可交付版本

如果时间不够，Plan 3 最小版只做：

```text
1. Qdrant
2. KnowledgeBase / Document / DocumentChunk 表
3. Markdown / TXT 解析
4. 简单 Chunking
5. Embedding Provider
6. Qdrant 写入
7. Vector Search
8. RAG Chat API
9. 前端上传文档
10. 前端展示回答和来源
```

可以延后：

```text
1. PDF 解析
2. Chunk 预览页面
3. search_knowledge_base 工具
4. rag_queries 记录
5. 删除知识库
6. 删除文档
7. 完整测试
```

不能延后：

```text
1. KnowledgeBase / Document / Chunk 数据模型
2. Embedding Provider 抽象
3. Qdrant 封装
4. RAG Prompt
5. 来源展示
```

如果按最小版本进入 Plan 4，必须先补齐以下桥接项：

```text
1. search_knowledge_base 工具可用，后续 Agent 和 Trace 能统一观察 RAG 调用
2. rag_queries 或等价查询记录可用，Plan 4 可以扩展为检索 Trace
3. document_chunks 至少包含 document_id、chunk_index、content、metadata、vector_id
4. RAG Query API 返回 answer、sources、retrieval metadata
5. Qdrant payload 中保留 knowledge_base_id、document_id、chunk_id
```

---

## 13. Plan 3 与 Plan 4 的衔接

Plan 3 完成后，项目具备：

```text
基础 Chat
多模型 Provider
Tool Calling
简单 Agent Loop
文件读取工具
知识库管理
文档上传
文档解析
Chunking
Embedding
Qdrant 向量存储
Naive RAG
来源展示
```

这为 Plan 4 打基础。

Plan 4 不需要重写 RAG，而是在 Plan 3 基础上优化：

```text
Plan 3：Naive RAG
    ↓
Plan 4：Trace + Advanced RAG + Evaluation
```

Plan 4 重点做：

```text
Trace Timeline
RAG 检索记录
Token / Cost / Latency 细化
Metadata Filtering
Hybrid Search
Parent-Child Retrieval
Rerank
RAG Evaluation
```

所以 Plan 3 的设计必须保留这些扩展点：

```text
1. Chunk 要有 metadata
2. Document 要有 file_type / hash / status
3. Vector payload 要包含 knowledge_base_id / document_id / chunk_id
4. Retriever 要封装成独立模块
5. RAG Prompt 要独立模块
6. Embedding Provider 要可替换
7. Vector Store 要可替换
```

不要在 Plan 3 里把 RAG 写死成一个函数，否则 Plan 4 会很难扩展。

---

## 14. Plan 3 完成后的简历表达

可以写成：

```text
在 AI Agent Lab 中设计并实现知识库与 Naive RAG 系统，支持 Markdown / TXT / PDF 文档上传、文本解析、Chunking、Embedding 向量化、Qdrant 向量存储、Top-K 语义检索、RAG Prompt 构造、基于知识库的问答生成和来源片段展示。同时将知识库检索封装为 Tool，使其可以被 Agent Runtime 调用，为后续 Advanced RAG、Evaluation 和 Agentic RAG 扩展提供基础。
```

---
