# Plan 4｜工程化 RAG：Trace + Advanced RAG + Evaluation

## 0. 子计划定位

Plan 4 对应项目总路线中的：

```text
Plan 4：工程化 RAG
对应阶段口径：Phase 4 Trace + 可观测性 + Phase 5 Advanced RAG + Evaluation
```

说明：

```text
当前总设计文档中，Plan 4 对应 Phase 4 + Phase 5：
Phase 4 负责 Trace + 可观测性；
Phase 5 负责 Advanced RAG + Evaluation。

本 PLAN4 按这个统一口径执行：
先把 Naive RAG 工程化，再把 Advanced RAG 和 Evaluation 接上。
```

Plan 4 的前置条件是：

```text
Plan 1 已完成
版本：v0.1.0
成果：基础 Chat 平台可运行

Plan 2 已完成
版本：v0.2.0
成果：Tool Calling + 简单 Agent Loop 可运行

Plan 3 已完成
版本：v0.3.0
成果：Knowledge Base + Document Ingestion + Naive RAG 可运行
```

也就是说，项目已经具备：

- FastAPI 后端

- React WebUI

- SQLite 会话存储

- LLM Provider 抽象

- Streaming Chat

- Tool Registry

- Simple Agent Loop

- Tool Call 记录

- Knowledge Base 管理

- 文档上传

- Markdown / TXT / PDF 文本解析

- Chunking

- Embedding Provider 抽象

- Qdrant Vector Store

- Naive Retriever

- RAG Query API

- RAG Chat API

- 来源片段展示

- search_knowledge_base 工具

Plan 4 不重写 Plan 3 的知识库系统。

Plan 4 的目标是在 Plan 3 的基础上增加：

> Trace 可观测性、RAG 检索过程记录、Advanced Retrieval 策略、Rerank、RAG Evaluation、策略对比页面，让系统不只是“能基于文档回答”，而是能解释为什么这样检索、为什么这样回答、哪种策略更好。

---

## 1. Plan 4 核心目标

Plan 4 的核心目标是：

> 把 Plan 3 的 Naive RAG 从“可用 Demo”升级为“可调试、可对比、可评测、可优化的工程化 RAG 系统”。

完成 Plan 4 后，系统应该支持：

```text
用户发起 RAG 问题
    -> 系统创建 trace run
    -> 记录 query、模型、知识库、策略配置
    -> 执行检索策略
    -> 记录每个召回候选 chunk、分数、来源、耗时
    -> 可选执行 Query Rewrite
    -> 可选执行 Hybrid Search
    -> 可选执行 Parent-Child Retrieval
    -> 可选执行 Rerank
    -> 构造 RAG Prompt
    -> 调用 LLM
    -> 记录 token、成本、延迟、prompt 版本
    -> 返回 answer + sources
    -> 前端展示 Timeline、检索结果、Rerank 分数和最终来源
```

同时支持：

```text
同一个问题
    -> 使用 Naive RAG 跑一次
    -> 使用 Hybrid + Rerank 跑一次
    -> 对比召回结果、答案质量、成本、延迟
    -> 在 Evaluation 页面看到指标差异
```

典型验收场景：

```text
用户上传一份技术文档。

用户提问：
这个项目为什么要设计 Provider 抽象？

系统可以展示：
1. 原始 query
2. 是否做了 query rewrite
3. 使用了哪个 retrieval strategy
4. Dense Search 召回了哪些 chunk
5. BM25 / Keyword Search 召回了哪些 chunk
6. Hybrid 融合后的排序
7. Rerank 后的最终来源
8. LLM 使用的 prompt 和 source
9. token / cost / latency
10. 最终答案
11. Evaluation 中该问题的 source hit / faithfulness / answer relevancy
```

Plan 4 的成果不是一个新聊天入口，而是：

> RAG 系统的工程化中台：可观测、可对比、可评测、可持续优化。

---

## 2. Plan 4 不做什么

为了控制范围，Plan 4 暂时不做：

| 暂不做 | 原因 |
| --- | --- |
| Memory 记忆系统 | 放到 Plan 5 或后续核心 Agent Runtime |
| ReAct Agent 强化 | Plan 2 已有 Simple Agent Loop，复杂 Agent Runtime 后移 |
| Planner-Executor | 与 RAG 工程化不是同一条主线 |
| Human Approval | 放到 Agent Runtime 阶段 |
| MCP | 放到后续 Agent 工作台阶段 |
| Voice / STT / TTS | 放到后续产品化阶段 |
| OCR / 图片 RAG | 放到多模态阶段 |
| GraphRAG | 研究价值高，但实现成本大，先不进 v0.4.0 |
| Agentic RAG | 依赖更强 Agent Runtime，Plan 4 只做可配置策略 |
| 全量 APM / LangSmith 级平台 | 本阶段做轻量自研 Trace，不追求生产级平台完整度 |
| 多租户权限系统 | 保持单用户学习项目边界 |
| 完美 Evaluation 学术指标 | 先做对学习和调试最有帮助的指标 |

Plan 4 只做：

> Trace + Advanced Retrieval + Rerank + RAG Evaluation 的可运行闭环。

---

## 3. Plan 4 版本目标

| 项目 | 内容 |
| --- | --- |
| 子计划名称 | Plan 4：工程化 RAG |
| 对应范围 | Trace + Observability + Advanced RAG + Evaluation |
| 起始版本 | v0.3.0 |
| 目标版本 | v0.4.0 |
| 核心能力 | 可观测 RAG、策略对比、Rerank、评测闭环 |
| 预计时间 | 150～230 小时 |
| 难度 | 高 |
| 项目价值 | 把项目从“能做 RAG”提升到“能分析和优化 RAG” |

---

## 4. Plan 4 技术重点

Plan 4 重点学习和实现：

- Trace Run / Trace Step 数据模型

- LLM 调用记录标准化

- RAG 检索过程记录

- Tool Call / Agent Run 与 Trace 的统一视图

- Token / Cost / Latency 细化

- Prompt Version 记录

- Metadata Filtering

- SQLite FTS5 / BM25 关键词检索

- Dense + Sparse Hybrid Search

- RRF 分数融合

- Parent-Child Retrieval

- Query Rewrite

- Rerank Provider 抽象

- Rerank API Provider

- RAG Strategy 配置

- RAG Evaluation Dataset

- Recall@K / MRR / Source Hit

- Faithfulness / Answer Relevancy

- LLM-as-Judge 初版

- Strategy Comparison UI

- Trace Timeline UI

---

## 5. Plan 4 推荐里程碑拆分

| 里程碑 | 名称 | 内容 | 预计时间 |
| --- | --- | --- | --- |
| M1 | Trace 基础设施 | Trace Run / Step、RAG 记录、Timeline API、基础 UI | 35～55 h |
| M2 | Advanced Retrieval | Metadata Filter、BM25、Hybrid、Parent-Child、Query Rewrite | 45～70 h |
| M3 | Rerank + Strategy | Rerank Provider、Advanced RAG API、策略配置和对比 | 30～45 h |
| M4 | Evaluation + 封版 | 测试集、评测指标、Eval 页面、测试、文档、v0.4.0 | 40～60 h |

Plan 4 的风险点是范围容易膨胀。

推荐优先级：

```text
必须完成：
Trace、RAG 检索记录、Hybrid Search、Rerank、基础 Evaluation

尽量完成：
Parent-Child、Query Rewrite、策略对比 UI

可以延期：
LLM-as-Judge 深度评测、复杂 Eval Dashboard、更多 Rerank Provider
```

---

## 6. Plan 4 推荐目录结构调整

在 Plan 3 基础上，后端新增：

```text
backend/app/
├── observability/
│   ├── trace_types.py
│   ├── trace_service.py
│   ├── trace_context.py
│   ├── token_cost.py
│   └── prompt_version.py
├── rag/
│   ├── strategies/
│   │   ├── base.py
│   │   ├── naive.py
│   │   ├── metadata_filter.py
│   │   ├── bm25.py
│   │   ├── hybrid.py
│   │   ├── parent_child.py
│   │   └── query_rewrite.py
│   ├── advanced_rag_service.py
│   ├── retrieval_recorder.py
│   └── strategy_registry.py
├── providers/
│   └── rerank/
│       ├── base.py
│       ├── openai_compatible.py
│       └── registry.py
├── evaluation/
│   ├── eval_types.py
│   ├── dataset_service.py
│   ├── rag_eval_runner.py
│   ├── metrics.py
│   ├── judge.py
│   └── report_service.py
├── models/
│   ├── trace.py
│   ├── retrieval.py
│   ├── rag_strategy.py
│   └── evaluation.py
├── schemas/
│   ├── trace.py
│   ├── retrieval.py
│   ├── rag_strategy.py
│   └── evaluation.py
└── api/v1/
    ├── traces.py
    ├── rag_advanced.py
    └── evaluations.py
```

前端新增：

```text
frontend/src/
├── pages/
│   ├── TracePage.tsx
│   ├── RagStrategyPage.tsx
│   └── EvaluationPage.tsx
├── components/
│   ├── trace/
│   │   ├── TraceTimeline.tsx
│   │   ├── TraceStepCard.tsx
│   │   ├── LlmCallPanel.tsx
│   │   ├── RetrievalTracePanel.tsx
│   │   └── CostLatencyPanel.tsx
│   ├── rag/
│   │   ├── RetrievalStrategySelector.tsx
│   │   ├── RetrievalResultTable.tsx
│   │   ├── RerankScoreList.tsx
│   │   └── StrategyComparePanel.tsx
│   └── evaluation/
│       ├── EvalDatasetList.tsx
│       ├── EvalCaseEditor.tsx
│       ├── EvalRunTable.tsx
│       └── EvalReportPanel.tsx
├── api/
│   ├── traces.ts
│   ├── ragAdvanced.ts
│   └── evaluations.ts
└── types/
    ├── trace.ts
    ├── ragStrategy.ts
    └── evaluation.ts
```

---

## 7. Plan 4 数据库设计

### 7.1 trace_runs

用于记录一次可观察的系统执行。

```sql
trace_runs
- id
- run_type
- conversation_id
- agent_run_id
- user_message_id
- title
- input_text
- output_text
- status
- provider
- model
- total_input_tokens
- total_output_tokens
- total_tokens
- estimated_cost
- latency_ms
- error_message
- metadata_json
- started_at
- ended_at
- created_at
```

`run_type` 建议：

```text
chat
agent
rag_query
rag_chat
evaluation
tool
```

Plan 4 不要求替换 Plan 1 的 `llm_calls` 或 Plan 2 的 `agent_runs/tool_calls`，而是用 `trace_runs` 做统一观察层。

---

### 7.2 trace_steps

用于记录一次 run 中的每个步骤。

```sql
trace_steps
- id
- trace_run_id
- step_index
- step_type
- name
- status
- input_json
- output_json
- error_message
- latency_ms
- started_at
- ended_at
- created_at
```

`step_type` 建议：

```text
build_context
llm_call
tool_call
rag_retrieve
query_rewrite
bm25_search
vector_search
hybrid_fusion
parent_child_expand
rerank
build_prompt
final_answer
eval_metric
```

---

### 7.3 rag_retrieval_runs

用于记录一次 RAG 检索。

```sql
rag_retrieval_runs
- id
- trace_run_id
- knowledge_base_id
- strategy_name
- original_query
- rewritten_query
- top_k
- candidate_count
- selected_count
- score_threshold
- latency_ms
- metadata_filter_json
- strategy_config_json
- created_at
```

---

### 7.4 rag_retrieval_candidates

用于记录每个候选 chunk 的召回和排序信息。

```sql
rag_retrieval_candidates
- id
- retrieval_run_id
- chunk_id
- document_id
- rank
- final_rank
- source
- dense_score
- sparse_score
- fused_score
- rerank_score
- selected
- content_preview
- metadata_json
- created_at
```

`source` 建议：

```text
dense
sparse
hybrid
parent
rerank
```

---

### 7.5 rag_strategies

用于保存可复用的 RAG 策略配置。

```sql
rag_strategies
- id
- name
- description
- strategy_type
- config_json
- is_default
- created_at
- updated_at
```

示例策略：

```json
{
  "name": "hybrid_rerank_default",
  "strategy_type": "hybrid_rerank",
  "config": {
    "dense_top_k": 20,
    "sparse_top_k": 20,
    "rrf_k": 60,
    "rerank_top_k": 5,
    "use_query_rewrite": false
  }
}
```

---

### 7.6 eval_datasets

用于管理评测数据集。

```sql
eval_datasets
- id
- name
- description
- dataset_type
- knowledge_base_id
- created_at
- updated_at
```

---

### 7.7 eval_cases

用于保存单条评测样例。

```sql
eval_cases
- id
- dataset_id
- question
- expected_answer
- expected_sources_json
- expected_keywords_json
- difficulty
- tags_json
- created_at
- updated_at
```

---

### 7.8 eval_runs

用于记录一次评测执行。

```sql
eval_runs
- id
- dataset_id
- strategy_id
- provider
- model
- status
- total_cases
- passed_cases
- failed_cases
- average_score
- total_cost
- latency_ms
- started_at
- ended_at
- created_at
```

---

### 7.9 eval_results

用于记录每条 case 的评测结果。

```sql
eval_results
- id
- eval_run_id
- eval_case_id
- trace_run_id
- answer
- retrieved_sources_json
- metrics_json
- score
- passed
- error_message
- created_at
```

---

## 8. Plan 4 核心接口设计

### 8.1 Trace API

```text
GET /api/v1/traces/runs
GET /api/v1/traces/runs/{trace_run_id}
GET /api/v1/traces/runs/{trace_run_id}/steps
GET /api/v1/traces/runs/{trace_run_id}/retrievals
GET /api/v1/traces/runs/{trace_run_id}/cost
DELETE /api/v1/traces/runs/{trace_run_id}
```

用途：

```text
让前端能够展示一次 RAG / Agent / Chat 执行的完整过程。
```

---

### 8.2 Advanced RAG API

```text
GET /api/v1/rag/strategies
POST /api/v1/rag/strategies
GET /api/v1/rag/strategies/{strategy_id}
PUT /api/v1/rag/strategies/{strategy_id}
DELETE /api/v1/rag/strategies/{strategy_id}

POST /api/v1/rag/query/advanced
POST /api/v1/rag/chat/advanced
POST /api/v1/rag/compare
```

`rag/query/advanced` 只返回检索和排序结果。

`rag/chat/advanced` 返回最终答案和来源。

`rag/compare` 用同一个问题跑多个策略，方便对比。

---

### 8.3 Evaluation API

```text
POST /api/v1/evaluations/datasets
GET /api/v1/evaluations/datasets
GET /api/v1/evaluations/datasets/{dataset_id}
DELETE /api/v1/evaluations/datasets/{dataset_id}

POST /api/v1/evaluations/datasets/{dataset_id}/cases
GET /api/v1/evaluations/datasets/{dataset_id}/cases
PUT /api/v1/evaluations/cases/{case_id}
DELETE /api/v1/evaluations/cases/{case_id}

POST /api/v1/evaluations/runs
GET /api/v1/evaluations/runs
GET /api/v1/evaluations/runs/{eval_run_id}
GET /api/v1/evaluations/runs/{eval_run_id}/results
```

---

## 9. Plan 4 核心数据结构

### 9.1 TraceRun

```python
class TraceRun:
    id: str
    run_type: str
    status: str
    input_text: str
    output_text: str | None
    provider: str | None
    model: str | None
    total_tokens: int | None
    estimated_cost: float | None
    latency_ms: int | None
    steps: list["TraceStep"]
```

---

### 9.2 TraceStep

```python
class TraceStep:
    id: str
    trace_run_id: str
    step_index: int
    step_type: str
    name: str
    status: str
    input: dict
    output: dict | None
    latency_ms: int | None
    error_message: str | None
```

---

### 9.3 RetrievalCandidate

```python
class RetrievalCandidate:
    chunk_id: str
    document_id: str
    content: str
    metadata: dict
    dense_score: float | None
    sparse_score: float | None
    fused_score: float | None
    rerank_score: float | None
    rank: int
    selected: bool
```

---

### 9.4 RagStrategy

```python
class RagStrategy:
    name: str
    strategy_type: str
    config: dict
```

策略类型建议：

```text
naive
metadata_filter
bm25
hybrid
parent_child
query_rewrite
hybrid_rerank
```

---

### 9.5 AdvancedRagRequest

```python
class AdvancedRagRequest:
    knowledge_base_id: str
    query: str
    strategy_id: str | None
    strategy_config: dict | None
    provider: str | None
    model: str | None
    top_k: int
    trace: bool
```

---

### 9.6 EvalCase

```python
class EvalCase:
    id: str
    question: str
    expected_answer: str | None
    expected_sources: list[str]
    expected_keywords: list[str]
    tags: list[str]
```

---

### 9.7 EvalResult

```python
class EvalResult:
    case_id: str
    answer: str
    retrieved_sources: list[dict]
    metrics: dict
    score: float
    passed: bool
```

---

## 10. Plan 4 详细步骤

## Step 1：确认 Plan 3 封版状态

### 要做什么

检查 v0.3.0 是否稳定。

### 检查清单

```text
[ ] 基础 Chat 可用
[ ] Tool Calling 可用
[ ] Simple Agent Loop 可用
[ ] Knowledge Base 可创建
[ ] Markdown / TXT / PDF 文本解析可用
[ ] Chunking 可用
[ ] Embedding Provider 可用
[ ] Qdrant 写入和检索可用
[ ] RAG Query API 可用
[ ] RAG Chat API 可用
[ ] 来源片段展示可用
[ ] search_knowledge_base 工具可用
[ ] 已创建 tag v0.3.0
```

### 完成标准

```text
Plan 4 不重写 Plan 3，只在其基础上增强 RAG 工程化能力。
```

### 预计时间

2～4 小时

---

## Step 2：设计 Trace 基础数据模型

### 要做什么

创建 `trace_runs` 和 `trace_steps`。

### 任务清单

```text
[ ] 创建 models/trace.py
[ ] 定义 TraceRun ORM
[ ] 定义 TraceStep ORM
[ ] 创建 schemas/trace.py
[ ] 创建 Alembic migration
[ ] 写基础数据库测试
```

### 为什么做

Plan 1/2/3 已经分别有 `llm_calls`、`tool_calls`、`rag_queries` 等记录，但它们是分散的。

Plan 4 需要一个统一的观察层，把 Chat、Tool、RAG、Eval 串成同一条执行轨迹。

### 完成标准

```text
可以创建一个 trace_run，并向其中追加多个 trace_step。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(observability): add trace run and step models
```

---

## Step 3：实现 Trace Service 和 Trace Context

### 要做什么

封装 Trace 写入逻辑，避免业务代码到处手写数据库记录。

### 任务清单

```text
[ ] 创建 observability/trace_service.py
[ ] 创建 create_run()
[ ] 创建 finish_run()
[ ] 创建 fail_run()
[ ] 创建 add_step()
[ ] 创建 finish_step()
[ ] 创建 fail_step()
[ ] 创建 observability/trace_context.py
[ ] 支持 context manager 风格记录步骤
```

### 示例流程

```text
with trace.step("rag_retrieve"):
    run retriever
```

### 完成标准

```text
业务代码可以用统一接口记录执行过程，不需要直接操作 Trace ORM。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(observability): add trace service
```

---

## Step 4：接入 LLM 调用 Trace

### 要做什么

让所有 LLM 调用都能记录 provider、model、prompt、token、成本、延迟和错误。

### 任务清单

```text
[ ] 梳理现有 llm_calls 记录
[ ] 创建 observability/token_cost.py
[ ] 统一 token usage 解析
[ ] 统一 cost 估算
[ ] 在 Chat API 中创建 trace_run
[ ] 在 RAG Chat 中记录 llm_call step
[ ] 记录 prompt_version
[ ] 错误时记录 provider error 类型
```

### 完成标准

```text
一次普通 Chat 或 RAG Chat 后，可以在 trace 中看到 LLM 调用步骤和 token / cost / latency。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(observability): trace llm calls
```

---

## Step 5：接入 RAG 检索 Trace

### 要做什么

记录 RAG 检索过程，不只记录最终 sources。

### 任务清单

```text
[ ] 创建 models/retrieval.py
[ ] 定义 rag_retrieval_runs
[ ] 定义 rag_retrieval_candidates
[ ] 创建 rag/retrieval_recorder.py
[ ] 在 naive retriever 中记录 candidates
[ ] 记录 query、top_k、score、document、chunk、metadata
[ ] 记录检索耗时
```

### 为什么做

RAG 优化的核心不是看最终答案，而是看：

```text
有没有召回正确片段
召回顺序是否合理
最终给 LLM 的 source 是否足够
```

### 完成标准

```text
一次 RAG Query 后，可以看到所有候选 chunk 的分数和排序。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(rag): record retrieval traces
```

---

## Step 6：实现 Trace API

### 要做什么

让前端可以读取 Trace。

### 任务清单

```text
[ ] 创建 api/v1/traces.py
[ ] GET /api/v1/traces/runs
[ ] GET /api/v1/traces/runs/{trace_run_id}
[ ] GET /api/v1/traces/runs/{trace_run_id}/steps
[ ] GET /api/v1/traces/runs/{trace_run_id}/retrievals
[ ] 支持按 run_type 过滤
[ ] 支持按 status 过滤
[ ] 支持分页
```

### 完成标准

```text
Swagger 可以查看 trace 列表和某一次 run 的完整步骤。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(observability): add trace api
```

---

## Step 7：实现前端 Trace Timeline

### 要做什么

实现基础可观测性页面。

### 页面功能

```text
[ ] Trace 列表
[ ] Trace 详情页
[ ] Timeline 展示 step
[ ] LLM 调用详情
[ ] RAG 检索候选列表
[ ] Token / Cost / Latency 展示
[ ] 错误信息展示
```

### 组件建议

```text
TracePage
TraceTimeline
TraceStepCard
LlmCallPanel
RetrievalTracePanel
CostLatencyPanel
```

### 完成标准

```text
用户可以点击一次 RAG 问答，看到从检索到生成的完整执行轨迹。
```

### 预计时间

14～22 小时

### 建议 commit

```text
feat(frontend): add trace timeline page
```

---

## Step 8：实现 Metadata Filtering

### 要做什么

让检索支持按文档元数据过滤。

### 任务清单

```text
[ ] 梳理 document_chunks metadata_json
[ ] 支持 knowledge_base_id 过滤
[ ] 支持 document_id 过滤
[ ] 支持 file_type 过滤
[ ] 支持 filename 过滤
[ ] 支持 heading 过滤
[ ] 在 Vector Store search 中传入 filter
[ ] 在 RAG Query API 中暴露 metadata_filter
```

### 示例请求

```json
{
  "knowledge_base_id": "kb_xxx",
  "query": "Provider 抽象有什么作用？",
  "metadata_filter": {
    "file_type": "md",
    "filename_contains": "architecture"
  }
}
```

### 完成标准

```text
用户可以限制只检索某个文档、某类文件或某个标题范围。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(rag): add metadata filtering
```

---

## Step 9：实现 BM25 / Keyword Search

### 要做什么

为 Hybrid Search 准备关键词召回能力。

### 初版建议

```text
优先使用 SQLite FTS5。
不要在 Plan 4 初版引入 Elasticsearch。
```

### 任务清单

```text
[ ] 创建 document_chunks_fts 虚拟表
[ ] 在 chunk 写入时同步 FTS
[ ] 创建 rag/strategies/bm25.py
[ ] 支持 keyword search
[ ] 返回 sparse_score
[ ] 记录 bm25_search trace_step
```

### 为什么做

纯向量检索对专有名词、函数名、文件名、精确术语不稳定。

BM25 可以补足语义检索的短板。

### 完成标准

```text
输入关键词或函数名时，BM25 可以召回包含精确词的 chunk。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(rag): add bm25 keyword search
```

---

## Step 10：实现 Hybrid Search

### 要做什么

融合 Dense Vector Search 和 BM25 Search。

### 推荐策略

```text
Dense Search top_k = 20
BM25 Search top_k = 20
使用 RRF 融合
最终返回 top_k = 5
```

### 任务清单

```text
[ ] 创建 rag/strategies/hybrid.py
[ ] 调用 vector retriever
[ ] 调用 bm25 retriever
[ ] 实现 RRF 融合
[ ] 合并重复 chunk
[ ] 记录 dense_score / sparse_score / fused_score
[ ] 写单元测试
```

### RRF 说明

```text
score = 1 / (k + rank)
默认 k = 60
```

### 完成标准

```text
同一个 query 可以同时利用语义召回和关键词召回，并在 Trace 中看到融合前后的排序。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(rag): add hybrid retrieval strategy
```

---

## Step 11：实现 Parent-Child Retrieval

### 要做什么

支持“小块检索，大块返回”。

### 设计建议

```text
child chunk：用于向量检索，粒度较小
parent chunk：用于返回给 LLM，包含更完整上下文
```

### 数据模型调整

```text
document_chunks 增加：
- chunk_type
- parent_chunk_id
- start_char
- end_char
```

`chunk_type`：

```text
parent
child
```

### 任务清单

```text
[ ] 扩展 document_chunks 表
[ ] 创建 parent chunk 生成逻辑
[ ] 创建 child chunk 生成逻辑
[ ] child chunk 写入向量库
[ ] 命中 child 后回查 parent
[ ] Trace 中记录 child hit 和 parent returned
[ ] 增加 reindex 文档能力
```

### 完成标准

```text
检索时命中精确 child，最终注入 Prompt 的是更完整的 parent 内容。
```

### 预计时间

14～22 小时

### 建议 commit

```text
feat(rag): add parent child retrieval
```

---

## Step 12：实现 Query Rewrite

### 要做什么

让系统可选地用 LLM 改写检索问题。

### 任务清单

```text
[ ] 创建 rag/strategies/query_rewrite.py
[ ] 定义 rewrite prompt
[ ] 支持关闭和开启
[ ] 记录 original_query
[ ] 记录 rewritten_query
[ ] 记录 rewrite LLM 调用成本
[ ] rewrite 失败时回退原始 query
```

### Prompt 建议

```text
请把用户问题改写为适合知识库检索的简洁查询。
保留关键名词、技术术语、文件名和英文缩写。
不要回答问题，只输出改写后的查询。
```

### 完成标准

```text
口语化问题可以被改写为更适合检索的 query，并且 Trace 可见。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(rag): add query rewrite strategy
```

---

## Step 13：设计 Rerank Provider 抽象

### 要做什么

定义统一 Rerank 接口。

### 核心结构

```python
class RerankDocument:
    id: str
    text: str
    metadata: dict

class RerankResult:
    document_id: str
    score: float
    rank: int

class BaseRerankProvider:
    async def rerank(self, query: str, documents: list[RerankDocument], top_k: int) -> list[RerankResult]:
        ...
```

### 任务清单

```text
[ ] 创建 providers/rerank/base.py
[ ] 定义 RerankDocument
[ ] 定义 RerankResult
[ ] 定义 BaseRerankProvider
[ ] 定义 RerankProviderError
[ ] 创建 providers/rerank/registry.py
```

### 完成标准

```text
业务层不直接依赖某一家 Rerank API。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(rerank): add rerank provider abstraction
```

---

## Step 14：实现 API Rerank Provider

### 要做什么

接入一个 OpenAI-compatible 或 Jina / BGE / Qwen 兼容的 rerank 服务。

### 任务清单

```text
[ ] 支持 base_url
[ ] 支持 api_key
[ ] 支持 model
[ ] 支持 query
[ ] 支持 documents
[ ] 支持 top_k
[ ] 解析 score
[ ] 统一错误处理
[ ] 记录 rerank trace_step
```

### 完成标准

```text
系统可以对召回的 20～30 个候选 chunk 进行重排，并返回最相关的 top_k。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(rerank): implement api rerank provider
```

---

## Step 15：实现 Advanced RAG Strategy Registry

### 要做什么

让不同 RAG 策略可以被配置、保存和复用。

### 任务清单

```text
[ ] 创建 models/rag_strategy.py
[ ] 创建 schemas/rag_strategy.py
[ ] 创建 rag/strategy_registry.py
[ ] 内置 naive 策略
[ ] 内置 hybrid 策略
[ ] 内置 hybrid_rerank 策略
[ ] 支持读取策略配置
[ ] 支持默认策略
```

### 完成标准

```text
前端可以列出当前可用 RAG 策略，用户可以选择策略执行问答。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(rag): add rag strategy registry
```

---

## Step 16：实现 Advanced RAG Query API

### 要做什么

实现可配置策略的检索接口。

### 接口

```text
POST /api/v1/rag/query/advanced
```

请求示例：

```json
{
  "knowledge_base_id": "kb_xxx",
  "query": "为什么要设计 Provider 抽象？",
  "strategy_name": "hybrid_rerank",
  "top_k": 5,
  "metadata_filter": {
    "file_type": "md"
  },
  "trace": true
}
```

返回示例：

```json
{
  "trace_run_id": "trace_xxx",
  "strategy_name": "hybrid_rerank",
  "results": [
    {
      "chunk_id": "chunk_xxx",
      "document_id": "doc_xxx",
      "content": "...",
      "dense_score": 0.72,
      "sparse_score": 9.4,
      "fused_score": 0.031,
      "rerank_score": 0.91
    }
  ]
}
```

### 完成标准

```text
Swagger 可以选择不同 RAG 策略并看到不同召回结果。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(rag): add advanced rag query api
```

---

## Step 17：实现 Advanced RAG Chat API

### 要做什么

把 Advanced Retrieval 接到最终问答流程。

### 接口

```text
POST /api/v1/rag/chat/advanced
```

流程：

```text
创建 trace_run
    -> 可选 query rewrite
    -> 执行 strategy retrieval
    -> 可选 rerank
    -> 构造 prompt
    -> 调用 LLM
    -> 保存 answer
    -> 返回 answer + sources + trace_run_id
```

### 完成标准

```text
用户可以基于 Hybrid + Rerank 的结果生成答案，并能查看完整 Trace。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(rag): add advanced rag chat api
```

---

## Step 18：实现 RAG Strategy Compare API

### 要做什么

用同一个问题对比多个策略。

### 接口

```text
POST /api/v1/rag/compare
```

请求示例：

```json
{
  "knowledge_base_id": "kb_xxx",
  "query": "项目的核心原则是什么？",
  "strategies": ["naive", "hybrid", "hybrid_rerank"],
  "top_k": 5
}
```

### 对比内容

```text
召回 chunk
最终 sources
答案文本
token
cost
latency
trace_run_id
```

### 完成标准

```text
同一个问题可以一次性跑多个策略，并返回对比结果。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(rag): add strategy comparison api
```

---

## Step 19：实现前端 RAG 策略配置和对比页面

### 要做什么

让用户可以选择、运行、对比 RAG 策略。

### 页面功能

```text
[ ] 策略列表
[ ] 策略详情
[ ] 策略选择器
[ ] Advanced RAG Query 调试
[ ] Retrieval Result 表格
[ ] dense / sparse / fused / rerank 分数展示
[ ] 多策略对比
[ ] 点击跳转 Trace
```

### 组件建议

```text
RagStrategyPage
RetrievalStrategySelector
RetrievalResultTable
RerankScoreList
StrategyComparePanel
```

### 完成标准

```text
用户可以在页面上比较 Naive RAG、Hybrid Search、Hybrid + Rerank 的差异。
```

### 预计时间

16～24 小时

### 建议 commit

```text
feat(frontend): add rag strategy comparison page
```

---

## Step 20：设计 Evaluation 数据模型

### 要做什么

创建 RAG 评测数据集、样例、运行记录和结果表。

### 任务清单

```text
[ ] 创建 models/evaluation.py
[ ] 定义 EvalDataset
[ ] 定义 EvalCase
[ ] 定义 EvalRun
[ ] 定义 EvalResult
[ ] 创建 schemas/evaluation.py
[ ] 创建 Alembic migration
[ ] 写数据库测试
```

### 完成标准

```text
可以创建一个评测数据集，并向其中加入多个 question / expected_sources。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(evaluation): add evaluation models
```

---

## Step 21：实现 Evaluation Dataset API

### 要做什么

实现评测数据集和测试样例管理。

### 任务清单

```text
[ ] 创建 evaluation/dataset_service.py
[ ] POST /api/v1/evaluations/datasets
[ ] GET /api/v1/evaluations/datasets
[ ] POST /api/v1/evaluations/datasets/{dataset_id}/cases
[ ] GET /api/v1/evaluations/datasets/{dataset_id}/cases
[ ] PUT /api/v1/evaluations/cases/{case_id}
[ ] DELETE /api/v1/evaluations/cases/{case_id}
```

### EvalCase 示例

```json
{
  "question": "AI Agent Lab 的核心目标是什么？",
  "expected_sources": ["00-project-overview.md"],
  "expected_keywords": ["学习型参考实现", "AI Agent", "工程工作台"]
}
```

### 完成标准

```text
用户可以维护一个小型 RAG 测试集。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(evaluation): add dataset api
```

---

## Step 22：实现 RAG Evaluation Runner

### 要做什么

对评测数据集批量运行 RAG 策略。

### 任务清单

```text
[ ] 创建 evaluation/rag_eval_runner.py
[ ] 输入 dataset_id
[ ] 输入 strategy_id
[ ] 遍历 eval_cases
[ ] 调用 advanced rag chat 或 query
[ ] 保存 trace_run_id
[ ] 保存 answer
[ ] 保存 retrieved_sources
[ ] 保存 eval_results
```

### 初版说明

```text
Plan 4 可以先同步执行评测。
如果数据集变大，后续再接入 Worker / Queue。
```

### 完成标准

```text
用户可以选择一个 dataset 和一个 RAG strategy，跑出一组 eval_results。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(evaluation): add rag evaluation runner
```

---

## Step 23：实现基础评测指标

### 要做什么

先实现可解释、低成本的指标。

### 指标范围

```text
[ ] Source Hit
[ ] Recall@K
[ ] MRR
[ ] Keyword Hit
[ ] Answer Contains
[ ] Latency
[ ] Token Cost
```

### 指标说明

```text
Source Hit：
只要 retrieved_sources 命中 expected_sources 中任意一个，即为命中。

Recall@K：
expected_sources 中有多少被 top_k sources 覆盖。

MRR：
第一个正确 source 出现在第几名。

Keyword Hit：
答案是否包含 expected_keywords。
```

### 完成标准

```text
每条 eval_result 都能看到一组 metrics_json 和总分。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(evaluation): add basic rag metrics
```

---

## Step 24：实现 LLM-as-Judge 初版

### 要做什么

用 LLM 对答案质量做轻量判断。

### 暂定评分项

```text
answer_relevancy
faithfulness
source_grounding
```

### 任务清单

```text
[ ] 创建 evaluation/judge.py
[ ] 定义 judge prompt
[ ] 输入 question / answer / sources / expected_answer
[ ] 输出 JSON 分数
[ ] 失败时不影响 rule-based metrics
[ ] 记录 judge LLM 调用成本
```

### 输出示例

```json
{
  "answer_relevancy": 0.8,
  "faithfulness": 0.9,
  "source_grounding": 0.85,
  "comment": "答案主要基于来源，但缺少一个关键约束。"
}
```

### 是否必须

```text
非必须。
如果时间紧，LLM-as-Judge 可以延期，但 rule-based metrics 不能延期。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(evaluation): add llm judge for rag answers
```

---

## Step 25：实现 Evaluation API

### 要做什么

对外暴露评测执行和结果查询接口。

### 任务清单

```text
[ ] POST /api/v1/evaluations/runs
[ ] GET /api/v1/evaluations/runs
[ ] GET /api/v1/evaluations/runs/{eval_run_id}
[ ] GET /api/v1/evaluations/runs/{eval_run_id}/results
[ ] 支持按 strategy 过滤
[ ] 支持按 dataset 过滤
```

### 完成标准

```text
Swagger 可以启动一次评测，并查看每条 case 的结果和指标。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(evaluation): add evaluation run api
```

---

## Step 26：实现前端 Evaluation 页面

### 要做什么

让用户可以管理测试集、运行评测、查看报告。

### 页面功能

```text
[ ] Eval Dataset 列表
[ ] Eval Case 编辑
[ ] 启动 Eval Run
[ ] Eval Run 列表
[ ] Eval Result 表格
[ ] 指标汇总
[ ] 策略对比
[ ] 点击查看对应 Trace
```

### 组件建议

```text
EvaluationPage
EvalDatasetList
EvalCaseEditor
EvalRunTable
EvalReportPanel
```

### 完成标准

```text
用户可以在页面上看到不同 RAG 策略的评测指标差异。
```

### 预计时间

16～24 小时

### 建议 commit

```text
feat(frontend): add evaluation page
```

---

## Step 27：补充 Plan 4 测试

### 要做什么

给 Trace、Advanced RAG、Evaluation 写基础测试。

### 测试范围

```text
[ ] TraceRun 创建测试
[ ] TraceStep 追加测试
[ ] LLM call trace mock 测试
[ ] RAG retrieval record 测试
[ ] Metadata filter 测试
[ ] BM25 search 测试
[ ] Hybrid RRF 融合测试
[ ] Parent-Child 回查测试
[ ] Query Rewrite fallback 测试
[ ] Rerank Provider mock 测试
[ ] Advanced RAG Query API 测试
[ ] Eval Dataset API 测试
[ ] Eval metrics 测试
[ ] Eval Runner mock 测试
```

### 完成标准

```text
核心策略和评测指标有测试，不依赖真实模型也能跑通主要逻辑。
```

### 预计时间

12～18 小时

### 建议 commit

```text
test(rag): add advanced rag and evaluation tests
```

---

## Step 28：补充 Plan 4 文档

### 要做什么

写清楚工程化 RAG 的设计。

### 文档建议

```text
docs/16-plan-4-engineering-rag.md
docs/17-trace-observability.md
docs/18-advanced-retrieval.md
docs/19-rerank-provider.md
docs/20-rag-evaluation.md
docs/21-rag-strategy-comparison.md
```

### 每篇文档写什么

```text
1. 模块目标
2. 为什么这样设计
3. 核心数据结构
4. API 说明
5. 当前限制
6. 如何从 Naive RAG 升级到 Advanced RAG
7. 如何阅读 Trace 和 Evaluation 结果
```

### 完成标准

```text
别人看文档能理解：
为什么 Naive RAG 不够；
Hybrid / Parent-Child / Rerank 分别解决什么问题；
Trace 和 Evaluation 如何帮助持续优化 RAG。
```

### 预计时间

8～12 小时

### 建议 commit

```text
docs: add plan 4 engineering rag documents
```

---

## Step 29：Plan 4 封版

### 要做什么

发布 v0.4.0。

### 任务清单

```text
[ ] 更新 README
[ ] 更新 CHANGELOG.md
[ ] 截图 Trace Timeline 页面
[ ] 截图 RAG 策略对比页面
[ ] 截图 Evaluation 页面
[ ] 记录当前支持的 RAG 策略
[ ] 记录当前评测指标
[ ] 记录当前限制
[ ] 创建 Git tag：v0.4.0
```

### 完成标准

```text
从 README 启动项目后，可以完成：
1. 上传文档并入库
2. 使用 Naive RAG 问答
3. 使用 Hybrid + Rerank 问答
4. 查看 Trace Timeline
5. 查看检索候选和 Rerank 分数
6. 用同一问题对比多个策略
7. 创建 RAG 测试集
8. 运行 Evaluation
9. 查看不同策略的指标差异
```

### 建议 commit

```text
chore: release v0.4.0 engineering rag
```

---

## 11. Plan 4 最终验收标准

Plan 4 完成后，必须满足：

```text
[ ] trace_runs 可用
[ ] trace_steps 可用
[ ] LLM 调用 Trace 可用
[ ] RAG 检索 Trace 可用
[ ] Trace API 可用
[ ] 前端 Trace Timeline 可用
[ ] Token / Cost / Latency 可见
[ ] Metadata Filtering 可用
[ ] BM25 / Keyword Search 可用
[ ] Hybrid Search 可用
[ ] RRF 融合可用
[ ] Parent-Child Retrieval 可用
[ ] Query Rewrite 可选可用
[ ] Rerank Provider 抽象完成
[ ] 至少一个 Rerank Provider 可用
[ ] Advanced RAG Query API 可用
[ ] Advanced RAG Chat API 可用
[ ] Strategy Compare API 可用
[ ] 前端 RAG 策略对比页面可用
[ ] Eval Dataset 可创建
[ ] Eval Case 可维护
[ ] Eval Runner 可执行
[ ] Source Hit / Recall@K / MRR / Keyword Hit 可计算
[ ] Evaluation 页面可查看结果
[ ] 核心测试已补充
[ ] README 已更新
[ ] docs 已更新
[ ] 已创建 v0.4.0 tag
```

---

## 12. Plan 4 最小可交付版本

如果时间不够，Plan 4 最小版本只做：

```text
1. TraceRun / TraceStep
2. RAG 检索候选记录
3. Trace Timeline 页面
4. Metadata Filtering
5. BM25 Search
6. Hybrid Search
7. Rerank Provider 抽象
8. 一个 Rerank Provider
9. Advanced RAG Query API
10. Advanced RAG Chat API
11. 基础 Eval Dataset
12. Source Hit / Recall@K / MRR
13. Evaluation Run API
14. README 和文档更新
```

可以延期：

```text
1. Parent-Child Retrieval 的完整 UI
2. Query Rewrite
3. LLM-as-Judge
4. 完整 Strategy Compare 页面
5. 更复杂的 Eval Dashboard
6. 多个 Rerank Provider
7. 异步 Evaluation Worker
```

不能延期：

```text
1. Trace 基础设施
2. RAG 检索记录
3. Hybrid Search
4. Rerank 抽象
5. 基础 Evaluation 指标
6. Trace / Evaluation 文档
```

如果按最小版本进入 Plan 5，必须先补齐以下桥接项：

```text
1. TraceRun / TraceStep 已覆盖 Chat、Tool Call、RAG Query 三类执行
2. Token / Cost / Latency 字段稳定，Plan 5 可以直接复用
3. RAG Evaluation 至少能评测一个固定测试集
4. Advanced RAG API 的 strategy 参数和返回结构稳定
5. Rerank Provider 抽象稳定，后续 Agent Runtime 不需要重写
```

---

## 13. Plan 4 与 Plan 5 的衔接

Plan 4 完成后，项目具备：

```text
基础 Chat
多模型 Provider
Tool Calling
简单 Agent Loop
知识库管理
文档上传和解析
Naive RAG
Advanced RAG
Rerank
RAG Trace
Timeline
RAG Evaluation
策略对比
Token / Cost / Latency 可观测
```

这为 Plan 5 的核心 Agent Runtime 打基础。

Plan 5 不需要再重新做：

```text
Trace 基础设施
Tool Call 记录
RAG 检索记录
RAG Evaluation
Provider 抽象
```

Plan 5 可以在 Plan 4 的基础上扩展：

```text
Memory 写入 Trace
Planner Step Trace
ReAct Thought / Action / Observation Trace
Human Approval Step
Retry / Error Recovery
Long-running Agent Run
Agent Task Evaluation
```

换句话说：

```text
Plan 4 让 RAG 可观察、可优化。
Plan 5 让 Agent Runtime 可观察、可恢复、可长期执行。
```

---

## 14. Plan 4 完成后的简历表达

可以写成：

```text
在 AI Agent Lab 中设计并实现工程化 RAG 模块，在 Naive RAG 基础上增加 Trace 可观测性、Hybrid Search、Metadata Filtering、Parent-Child Retrieval、Rerank、策略对比和 RAG Evaluation。系统支持记录每次 RAG 问答的检索候选、召回分数、Rerank 分数、Prompt、Token、成本和延迟，并通过前端 Timeline 展示完整执行过程。同时实现 RAG 测试集、Source Hit、Recall@K、MRR 等评测指标，用于比较 Naive RAG、Hybrid Search 和 Hybrid + Rerank 等不同策略的效果。
```

亮点可以拆成：

```text
1. 设计统一 Trace Run / Step 模型，串联 Chat、Tool、RAG、Evaluation 的执行过程。
2. 实现 Dense Vector Search + BM25 的 Hybrid Retrieval，并使用 RRF 做结果融合。
3. 接入 Rerank Provider，对召回候选进行精排，提高最终上下文质量。
4. 建立 RAG Evaluation 数据集和指标体系，支持策略效果量化对比。
5. 构建 Trace Timeline 和 Strategy Compare 页面，让 RAG 系统具备工程调试能力。
```

---

## 15. 当前结构口径

Plan 4 与总设计文档保持一致：

```text
Plan 4 = Phase 4 Trace + 可观测性 + Phase 5 Advanced RAG + Evaluation
Plan 5 = Phase 6 Memory + Agent Runtime 强化
Plan 6 = Phase 7 MCP + 工程扩展 + Phase 8 语音 / 多模态 / 桌面端
Phase 9 = 多 Agent（后期扩展）
```

执行时不要再把 Evaluation 或 Observability 放到更靠后的阶段。
Plan 4 的核心价值就是让 RAG 从“能回答”升级为“可观察、可比较、可评测、可持续优化”。
