# Plan 4 执行步骤表｜Trace + Advanced RAG + Evaluation

> 适用文档：`00-ALL PLAN/04-PLAN-4 (V1.0).md`  
> 执行方式：每次只领取连续 1～3 个 Step，完成后立即测试、提交、review。  
> 阶段目标：一个阶段完成一个里程碑；一个里程碑通过后再进入下一个里程碑。

---

## 0. 执行总原则

| 规则 | 说明 |
|---|---|
| 单次执行范围 | Cursor / Codex 每次只做 1～3 个连续 Step |
| 执行顺序 | 必须按 `P4-Mx-Sy` 顺序推进，除非 Codex 明确调整 |
| 每步完成定义 | 代码可运行、局部测试通过、相关文档或配置同步 |
| 每个阶段完成定义 | 阶段验收项全部通过，Codex review 后进入下一阶段 |
| Claude Code 使用时机 | Trace 模型、Hybrid Retrieval、Rerank/Strategy、Evaluation Runner 完成后 |
| 提交节奏 | 每 1～3 个 Step 一次 commit；每个里程碑结束一次 review commit |
| 文档同步 | Trace 数据结构、策略参数、评测指标、API 返回结构变化必须同步 docs 或 README |
| 禁止提前做 | Memory、复杂 Agent Runtime、Planner-Executor、Human Approval、MCP、多模态、GraphRAG |

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

## 1. Plan 4 总览

| 阶段 | 里程碑 | 对应原 PLAN4 Step | 核心交付 | 预计时间 | 主要工具 | 审核节点 |
|---|---|---|---|---:|---|---|
| Phase 1 | M1 交接与 Trace 基础设施 | Step 1～3 | v0.3.0 检查、TraceRun / TraceStep、Trace Service / Context | 20～30 h | Codex | Codex + Claude Code |
| Phase 2 | M2 Trace 接入与 Timeline | Step 4～7 | LLM Trace、RAG Trace、Trace API、前端 Timeline | 25～40 h | Codex + Cursor | Codex + Claude Code |
| Phase 3 | M3 Advanced Retrieval 基础 | Step 8～10 | Metadata Filtering、BM25 / Keyword Search、Hybrid Search、RRF | 25～40 h | Codex | Codex + Claude Code |
| Phase 4 | M4 Retrieval 扩展策略 | Step 11～12 | Parent-Child Retrieval、Query Rewrite | 20～35 h | Codex | Codex review |
| Phase 5 | M5 Rerank + Strategy + Advanced API | Step 13～19 | Rerank Provider、Strategy Registry、Advanced RAG API、Strategy Compare、前端策略页 | 35～55 h | Codex + Cursor | Codex + Claude Code |
| Phase 6 | M6 Evaluation 闭环 | Step 20～26 | Eval 数据模型、Dataset API、Runner、指标、Evaluation API、前端 Eval 页面 | 35～55 h | Codex + Cursor | Codex + Claude Code |
| Phase 7 | M7 测试、文档与封版 | Step 27～29 | 测试、README、docs、截图、CHANGELOG、v0.4.0 tag | 10～20 h | Codex + Cursor | Codex + Claude Code |

---

## 2. 执行节奏表

| 执行批次 | 建议领取范围 | 批次目标 | 完成后动作 |
|---|---|---|---|
| Batch 1 | P4-M1-S1～S3 | 确认 Plan3 地基，建立 Trace 数据模型 | 迁移和模型测试 |
| Batch 2 | P4-M1-S4～S6 | 实现 Trace Service / Context / Step writer | Trace 单元测试 |
| Batch 3 | P4-M1-S7 | 完成 Trace 基础文档和 M1 review | Codex + Claude review M1 |
| Batch 4 | P4-M2-S1～S3 | 接入 LLM 调用 Trace 和成本记录 | LLM Trace 测试 |
| Batch 5 | P4-M2-S4～S6 | 接入 RAG 检索 Trace 和候选记录 | RAG Trace 测试 |
| Batch 6 | P4-M2-S7～S9 | 实现 Trace API 和前端 Timeline | API 测试 + 浏览器手测 |
| Batch 7 | P4-M2-S10 | 完成 Timeline review | Codex + Claude review M2 |
| Batch 8 | P4-M3-S1～S3 | 实现 metadata filter 和策略接口基础 | Retriever 测试 |
| Batch 9 | P4-M3-S4～S6 | 实现 BM25 / keyword search | 搜索测试 |
| Batch 10 | P4-M3-S7～S9 | 实现 Hybrid Search 和 RRF 融合 | Hybrid 测试，Codex + Claude review M3 |
| Batch 11 | P4-M4-S1～S3 | 实现 Parent-Child Retrieval | 检索测试 |
| Batch 12 | P4-M4-S4～S6 | 实现 Query Rewrite 和 fallback | rewrite 测试，Codex review M4 |
| Batch 13 | P4-M5-S1～S3 | 设计并实现 Rerank Provider 抽象 | provider mock 测试 |
| Batch 14 | P4-M5-S4～S6 | 实现 API Rerank Provider 和 Strategy Registry | rerank / strategy 测试 |
| Batch 15 | P4-M5-S7～S9 | 实现 Advanced RAG Query / Chat API | API 测试 |
| Batch 16 | P4-M5-S10～S12 | 实现 Strategy Compare API 和前端策略页 | 浏览器手测，Codex + Claude review M5 |
| Batch 17 | P4-M6-S1～S3 | 实现 Evaluation 数据模型和 Dataset API | eval model / API 测试 |
| Batch 18 | P4-M6-S4～S6 | 实现 Evaluation Runner 和基础指标 | runner / metrics 测试 |
| Batch 19 | P4-M6-S7～S9 | 实现 Evaluation API、可选 LLM-as-Judge、前端 Eval 页面 | API + 页面验证，Codex + Claude review M6 |
| Batch 20 | P4-M7-S1～S6 | 补测试、文档、截图、封版 | Codex + Claude final review |

---

## 3. Phase 1｜M1 交接与 Trace 基础设施

阶段目标：

```text
确认 v0.3.0 Naive RAG 底座稳定，建立统一 TraceRun / TraceStep 模型和 Trace Service，为 Chat、Tool、RAG、Evaluation 的可观测性打地基。
```

阶段验收：

```text
1. Plan 3 的 Knowledge Base、Document Ingestion、Naive RAG、search_knowledge_base 工具仍可用
2. trace_runs / trace_steps 数据模型可用
3. Trace Service 可以创建 run、写入 step、结束 run、记录错误
4. Trace Context 可以贯穿一次请求
5. Trace 结构保留 Plan 5 Agent Runtime 复用空间
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P4-M1-S1 | 检查 Plan 3 封版状态和 v0.3.0 tag | Codex | Plan 3 验收记录 | RAG Query、RAG Chat、search_knowledge_base 均可用或有明确证据 | Codex |
| P4-M1-S2 | 设计 TraceRun / TraceStep ORM 和 schema | Codex | `trace_runs`、`trace_steps` 模型和 schema | 迁移和模型测试通过 | Claude Code 可审 |
| P4-M1-S3 | 定义 Trace step 类型和状态枚举 | Codex | `observability/trace_types.py` | step type / status 序列化测试通过 | Codex |
| P4-M1-S4 | 实现 Trace Service | Codex | `observability/trace_service.py` | create_run、add_step、finish_run、fail_run 测试通过 | Codex |
| P4-M1-S5 | 实现 Trace Context | Codex | `observability/trace_context.py` | 同一请求内能读取 trace_run_id | Codex |
| P4-M1-S6 | 实现 token / cost / latency 辅助记录结构 | Codex | `observability/token_cost.py` | mock LLM usage 可写入 step metadata | Codex |
| P4-M1-S7 | 完成 Trace 基础文档和 M1 review | Codex | `docs/30-trace-observability.md` 初版 | 文档说明 TraceRun / TraceStep 字段和生命周期 | Codex + Claude review |

M1 完成后建议 commit：

```text
feat(observability): add trace run step and context
```

---

## 4. Phase 2｜M2 Trace 接入与 Timeline

阶段目标：

```text
把 Trace 接入 LLM 调用和 RAG 检索过程，并提供 Trace API 与前端 Timeline，让一次 RAG 请求可复盘。
```

阶段验收：

```text
1. LLM 调用会写入 trace step
2. RAG 检索会记录 query、strategy、候选 chunk、score、source、latency
3. Trace API 可以查询 run、steps、related metadata
4. 前端 Trace Timeline 可以展示 LLM / Retrieval / Rerank / Error 等步骤
5. Token / Cost / Latency 可见
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P4-M2-S1 | 接入 LLM 调用 Trace | Codex | provider 或 chat service trace hook | 一次 Chat 产生 LLM trace step | Codex |
| P4-M2-S2 | 标准化 LLM step metadata | Codex | prompt version、model、provider、usage、latency metadata | metadata schema 测试通过 | Codex |
| P4-M2-S3 | 接入 LLM 错误 Trace | Codex | error step / failed status | 模拟 provider error 能写入 trace | Codex |
| P4-M2-S4 | 设计 RAG retrieval run / candidate 模型 | Codex | `rag_retrieval_runs`、`rag_retrieval_candidates` | 迁移和模型测试通过 | Claude Code 可审 |
| P4-M2-S5 | 接入 Naive Retriever Trace | Codex | retrieval trace writer | RAG Query 写入候选 chunk 和 score | Codex |
| P4-M2-S6 | 接入 RAG Prompt / Answer Trace | Codex | prompt 和 answer step | Trace 中能看到 prompt 版本、sources、answer metadata | Codex |
| P4-M2-S7 | 实现 Trace API | Codex | `api/v1/traces.py` | 查询 trace run / steps / candidates 测试通过 | Codex |
| P4-M2-S8 | 创建前端 Trace API 封装和类型 | Cursor | `frontend/src/api/traces.ts`、types | TypeScript 检查通过 | Codex |
| P4-M2-S9 | 实现前端 Trace Timeline 页面 | Cursor | `TraceTimelinePage.tsx`、step timeline 组件 | 浏览器可查看一次 RAG 请求 Timeline | Codex |
| P4-M2-S10 | 完成 M2 review 和 Trace 使用文档 | Codex | `docs/31-trace-timeline.md` | Timeline 手测记录和文档齐全 | Codex + Claude review |

M2 完成后建议 commit：

```text
feat(observability): trace llm rag and timeline
```

---

## 5. Phase 3｜M3 Advanced Retrieval 基础

阶段目标：

```text
在 Plan 3 Retriever 基础上增加 Metadata Filtering、BM25 / Keyword Search、Hybrid Search 和 RRF 融合。
```

阶段验收：

```text
1. Metadata filter 可以按 knowledge_base_id、document_id、file_type、tags 等过滤
2. BM25 / Keyword Search 可用
3. Dense Search 与 Keyword Search 能统一为候选列表
4. Hybrid Search 使用 RRF 融合结果
5. 每种检索策略都能写入 retrieval trace
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P4-M3-S1 | 抽象 Retrieval Strategy 基类 | Codex | `rag/strategies/base.py` | naive strategy 适配测试通过 | Claude Code 可审 |
| P4-M3-S2 | 实现 Metadata Filtering | Codex | `metadata_filter.py` | 按 document_id / file_type / metadata 过滤测试通过 | Codex |
| P4-M3-S3 | 将过滤条件接入 vector search payload | Codex | Qdrant filter builder | Qdrant filter 结构测试通过 | Codex |
| P4-M3-S4 | 建立 keyword index 策略 | Codex | SQLite FTS5 或本地 BM25 service | 文档 chunk 可索引 | Claude Code 可审 |
| P4-M3-S5 | 实现 BM25 / Keyword Search | Codex | `keyword_search.py` | 关键词 query 返回候选 chunk | Codex |
| P4-M3-S6 | 标准化 dense / sparse candidate 结构 | Codex | `RetrievalCandidate` schema | dense / keyword 候选字段一致 | Codex |
| P4-M3-S7 | 实现 RRF 融合 | Codex | `fusion.py` | 已知排序输入能得到预期融合排序 | Codex |
| P4-M3-S8 | 实现 Hybrid Search Strategy | Codex | `hybrid.py` | dense + keyword + RRF 端到端测试通过 | Codex |
| P4-M3-S9 | 将 Advanced Retrieval 写入 Trace | Codex | strategy trace writer | Trace 展示 dense、keyword、hybrid 候选 | Codex + Claude review |

M3 完成后建议 commit：

```text
feat(rag): add metadata bm25 hybrid retrieval
```

---

## 6. Phase 4｜M4 Retrieval 扩展策略

阶段目标：

```text
实现 Parent-Child Retrieval 和 Query Rewrite，作为 Advanced RAG 的可选增强策略。
```

阶段验收：

```text
1. DocumentChunk 支持 parent_id 或等价 parent-child 关系
2. 检索小 chunk 后可回查 parent chunk
3. Query Rewrite 可选启用
4. Query Rewrite 失败时 fallback 到原始 query
5. Parent-Child 和 Query Rewrite 均可进入 Trace
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P4-M4-S1 | 扩展 DocumentChunk parent-child 字段和迁移 | Codex | parent_id / parent metadata | 迁移和模型测试通过 | Codex |
| P4-M4-S2 | 实现 Parent-Child Retrieval | Codex | `parent_child.py` | 子 chunk 命中后能回查 parent content | Claude Code 可审 |
| P4-M4-S3 | 接入 Parent-Child Trace | Codex | parent-child trace metadata | Trace 展示 child hit 和 parent expansion | Codex |
| P4-M4-S4 | 实现 Query Rewrite Prompt 和 service | Codex | `query_rewrite.py`、prompt | mock LLM rewrite 测试通过 | Codex |
| P4-M4-S5 | 接入 Query Rewrite fallback | Codex | rewrite failure handling | rewrite 失败时使用原 query | Codex |
| P4-M4-S6 | 完成 M4 review 和策略文档 | Codex | `docs/32-advanced-retrieval.md` | 文档说明 Parent-Child / Query Rewrite 限制 | Codex review |

M4 完成后建议 commit：

```text
feat(rag): add parent child retrieval and query rewrite
```

---

## 7. Phase 5｜M5 Rerank + Strategy + Advanced API

阶段目标：

```text
建立 Rerank Provider、Advanced RAG Strategy Registry、Advanced RAG Query / Chat API、Strategy Compare API 和前端策略配置页面。
```

阶段验收：

```text
1. Rerank Provider 抽象稳定
2. 至少一个 API Rerank Provider 或 mock provider 可用
3. Strategy Registry 可以组合 metadata、hybrid、parent-child、rewrite、rerank
4. Advanced RAG Query / Chat API 返回 answer、sources、strategy、trace_run_id、retrieval metadata
5. Strategy Compare API 能对同一问题跑多个策略
6. 前端能配置策略并查看对比结果
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P4-M5-S1 | 设计 RerankProvider 抽象 | Codex | `providers/rerank/base.py` | mock rerank provider 测试通过 | Claude Code 可审 |
| P4-M5-S2 | 定义 RerankResult 和 candidate 输入结构 | Codex | rerank schema | candidate 排序字段稳定 | Codex |
| P4-M5-S3 | 实现 Rerank Provider Registry | Codex | `providers/rerank/registry.py` | 可按配置选择 reranker | Codex |
| P4-M5-S4 | 实现 API Rerank Provider | Codex | API rerank provider | mock HTTP 响应解析测试通过 | Codex |
| P4-M5-S5 | 将 Rerank 接入 Advanced Retrieval | Codex | rerank step | Top-K rerank 后来源排序改变 | Codex |
| P4-M5-S6 | 将 Rerank 分数写入 Trace | Codex | rerank trace metadata | Timeline 可查看 before / after rerank | Codex |
| P4-M5-S7 | 实现 Advanced RAG Strategy Registry | Codex | `rag/strategies/registry.py` | naive、hybrid、hybrid+rerank 策略可选 | Claude Code 可审 |
| P4-M5-S8 | 实现 Advanced RAG Query API | Codex | `POST /api/v1/rag/advanced/query` | strategy 参数和返回结构测试通过 | Codex |
| P4-M5-S9 | 实现 Advanced RAG Chat API | Codex | `POST /api/v1/rag/advanced/chat` | 会话写入和 sources 返回测试通过 | Codex |
| P4-M5-S10 | 实现 Strategy Compare API | Codex | `POST /api/v1/rag/strategies/compare` | 同一 query 多策略结果对比测试通过 | Codex |
| P4-M5-S11 | 实现前端 RAG 策略配置页面 | Cursor | strategy config UI | 可选择 naive / hybrid / rerank 等配置 | Codex |
| P4-M5-S12 | 实现前端策略对比结果展示 | Cursor + Codex | compare result UI | 展示来源、分数、成本、延迟、trace 链接 | Codex + Claude review |

M5 完成后建议 commit：

```text
feat(rag): add rerank strategy registry and advanced rag api
```

---

## 8. Phase 6｜M6 Evaluation 闭环

阶段目标：

```text
建立 RAG Evaluation 的数据集、用例、运行器、基础指标、Evaluation API 和前端页面。
```

阶段验收：

```text
1. Eval Dataset / Eval Case / Eval Run / Eval Result 数据模型可用
2. 可以创建和维护 RAG 测试集
3. Evaluation Runner 能对固定测试集运行指定 RAG strategy
4. Source Hit / Recall@K / MRR / Keyword Hit 可计算
5. Evaluation API 可查看 run 和 result
6. Evaluation 页面可展示策略效果差异
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P4-M6-S1 | 设计 Evaluation 数据模型和迁移 | Codex | EvalDataset、EvalCase、EvalRun、EvalResult | 迁移和模型测试通过 | Claude Code 可审 |
| P4-M6-S2 | 实现 Evaluation Dataset API | Codex | dataset / case CRUD API | API 测试通过 | Codex |
| P4-M6-S3 | 实现 EvalCase 导入和样例数据 | Codex | seed 或导入接口 | 可创建固定测试集 | Codex |
| P4-M6-S4 | 实现 RAG Evaluation Runner | Codex | `evaluation/rag_runner.py` | 对固定 cases 执行指定 strategy | Claude Code 可审 |
| P4-M6-S5 | 实现基础评测指标 | Codex | Source Hit、Recall@K、MRR、Keyword Hit | 指标单元测试通过 | Codex |
| P4-M6-S6 | 持久化 EvalRun / EvalResult | Codex | result writer | run 状态和每 case 结果可查询 | Codex |
| P4-M6-S7 | 可选实现 LLM-as-Judge 初版 | Codex | judge provider / prompt | 若启用，输出 faithfulness / answer relevancy；若延期，记录限制 | Codex |
| P4-M6-S8 | 实现 Evaluation API | Codex | `api/v1/evaluation.py` | 创建 run、查询 run、查询 result 测试通过 | Codex |
| P4-M6-S9 | 实现前端 Evaluation 页面 | Cursor + Codex | dataset、run、results UI | 页面可查看指标和策略差异 | Codex + Claude review |

M6 完成后建议 commit：

```text
feat(evaluation): add rag evaluation datasets runner and metrics
```

---

## 9. Phase 7｜M7 测试、文档与封版

阶段目标：

```text
补齐 Plan 4 的测试、文档、截图、CHANGELOG 和 v0.4.0 tag，让工程化 RAG 成为可展示、可复盘、可继续扩展到 Plan 5 的稳定版本。
```

阶段验收：

```text
1. Trace、Advanced Retrieval、Rerank、Evaluation 核心测试通过
2. 前端 Timeline、Strategy Compare、Evaluation 页面有手动验证或截图
3. README 和 docs 说明 v0.4.0 新能力、配置、限制
4. CHANGELOG 记录 v0.4.0
5. 创建 v0.4.0 tag
6. Plan 4 到 Plan 5 的桥接检查通过
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P4-M7-S1 | 补 Trace / Timeline 测试 | Codex | observability tests | trace run / step / API 测试通过 | Codex |
| P4-M7-S2 | 补 Advanced Retrieval / Rerank 测试 | Codex | strategy / rerank tests | metadata、BM25、hybrid、rerank 测试通过 | Codex |
| P4-M7-S3 | 补 Evaluation 测试 | Codex | evaluation tests | runner、metrics、API 测试通过 | Codex |
| P4-M7-S4 | 补前端验证和截图 | Cursor + Codex | Timeline、Strategy Compare、Evaluation 截图 | 浏览器手测记录齐全 | Codex |
| P4-M7-S5 | 更新 README、docs、CHANGELOG | Codex | 文档和版本记录 | 文档覆盖 Trace、Advanced RAG、Evaluation、限制 | Codex |
| P4-M7-S6 | Plan 4 全量 review、修复、创建 v0.4.0 tag | Codex + Claude Code | review 记录、修复 commit、tag、桥接检查表 | 全量测试通过，tag 存在 | Codex + Claude final review |

M7 完成后建议 commit：

```text
chore: release v0.4.0 engineering rag
```

---

## 10. 每次执行 1～3 步的标准流程

每次让 Codex / Cursor 执行时，建议按这个模板下发：

```text
当前执行范围：P4-Mx-Sy ～ P4-Mx-Sz
必须遵守：只做这些 Step，不提前做 Memory、复杂 Agent Runtime、MCP 或多模态
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
2. 是否引入超出 Plan 4 的 Agent Runtime / Memory 能力
3. 是否破坏 Plan 3 的 Naive RAG API 和 search_knowledge_base 工具
4. Trace 是否完整记录 run、step、latency、error 和关键 metadata
5. Advanced RAG API 的 strategy 参数和返回结构是否稳定
6. Evaluation 指标是否有可重复测试集
7. 是否同步 README / docs / env example
8. 是否适合进入下一批次
```

---

## 11. Claude Code Review 节点

Claude Code 不需要每个 Step 都参与，建议在这些节点使用：

| 节点 | 审核重点 | 输入材料 |
|---|---|---|
| M1 结束 | TraceRun / TraceStep 模型能否支撑 Chat、Tool、RAG、Plan 5 Runtime | diff、ORM、schema、Trace Service、测试结果 |
| M2 结束 | LLM / RAG Trace 接入是否完整，Timeline 是否真实可复盘 | diff、trace hooks、Trace API、前端 Timeline、测试结果 |
| M3 结束 | Metadata / BM25 / Hybrid / RRF 抽象是否稳定 | diff、strategy 代码、candidate schema、retrieval tests |
| M5 结束 | Rerank Provider、Strategy Registry、Advanced RAG API 是否可扩展 | diff、provider、strategy、API、前端策略页、测试结果 |
| M6 结束 | Evaluation Runner 和指标是否可信 | diff、Eval 模型、runner、metrics、测试集、测试结果 |
| M7 封版前 | v0.4.0 是否能作为 Plan 5 Agent Runtime 的可观测和评测底座 | 全量 diff、README、测试结果、CHANGELOG、桥接检查 |

Claude Code 审核后，Codex 负责：

```text
1. 判断哪些意见必须修
2. 拆成 1～3 个修复 Step
3. 修复后重新跑测试
4. 更新文档和 changelog
```

---

## 12. Plan 4 最终验收清单

| 验收项 | 状态 | 证据 |
|---|---|---|
| trace_runs 可用 | pending | ORM / migration / test |
| trace_steps 可用 | pending | ORM / migration / test |
| LLM 调用 Trace 可用 | pending | LLM trace 测试 |
| RAG 检索 Trace 可用 | pending | RAG trace 测试 |
| Trace API 可用 | pending | API 测试 |
| 前端 Trace Timeline 可用 | pending | 页面截图 |
| Token / Cost / Latency 可见 | pending | trace metadata 或页面截图 |
| Metadata Filtering 可用 | pending | strategy 测试 |
| BM25 / Keyword Search 可用 | pending | keyword search 测试 |
| Hybrid Search 可用 | pending | hybrid strategy 测试 |
| RRF 融合可用 | pending | fusion 测试 |
| Parent-Child Retrieval 可用 | pending | parent-child 测试 |
| Query Rewrite 可选可用 | pending | rewrite 测试或延期说明 |
| Rerank Provider 抽象完成 | pending | provider 测试 |
| 至少一个 Rerank Provider 可用 | pending | provider 或 mock provider 测试 |
| Advanced RAG Query API 可用 | pending | API 测试 |
| Advanced RAG Chat API 可用 | pending | API 测试 |
| Strategy Compare API 可用 | pending | compare 测试 |
| 前端 RAG 策略对比页面可用 | pending | 页面截图 |
| Eval Dataset 可创建 | pending | API 测试 |
| Eval Case 可维护 | pending | API 测试 |
| Eval Runner 可执行 | pending | runner 测试 |
| Source Hit / Recall@K / MRR / Keyword Hit 可计算 | pending | metrics 测试 |
| Evaluation 页面可查看结果 | pending | 页面截图 |
| 核心测试已补充 | pending | 测试输出 |
| README 已更新 | pending | README 链接 |
| docs 已更新 | pending | docs 链接 |
| 已创建 v0.4.0 tag | pending | `git tag --list` 输出 |

---

## 13. Plan 4 到 Plan 5 的桥接检查

只有下面 5 项都满足，才建议进入 Plan 5：

| 桥接项 | 状态 | 说明 |
|---|---|---|
| TraceRun / TraceStep 已覆盖 Chat、Tool Call、RAG Query 三类执行 | pending | Plan 5 Agent Runtime 可以复用同一套可观测模型 |
| Token / Cost / Latency 字段稳定 | pending | Plan 5 可以直接记录 Agent step 成本 |
| RAG Evaluation 至少能评测一个固定测试集 | pending | Plan 5 Agent Evaluation 可以参考同一套评测思想 |
| Advanced RAG API 的 strategy 参数和返回结构稳定 | pending | Agent Runtime 可安全调用 Advanced RAG |
| Rerank Provider 抽象稳定 | pending | 后续 Agent Runtime 不需要重写排序能力 |

---

## 14. 推荐文件位置

执行过程中建议把相关产物放在这些位置：

| 类型 | 路径 |
|---|---|
| Trace 模型 | `backend/app/models/trace_run.py`、`backend/app/models/trace_step.py` |
| Trace 服务 | `backend/app/observability/trace_service.py`、`trace_context.py`、`trace_types.py` |
| Trace API | `backend/app/api/v1/traces.py` |
| Trace 前端 | `frontend/src/pages/TraceTimelinePage.tsx`、`frontend/src/components/trace/` |
| Retrieval 策略 | `backend/app/rag/strategies/` |
| Keyword / BM25 | `backend/app/rag/keyword_search.py` 或 `backend/app/rag/strategies/keyword.py` |
| RRF 融合 | `backend/app/rag/strategies/fusion.py` |
| Rerank Provider | `backend/app/providers/rerank/` |
| Advanced RAG API | `backend/app/api/v1/advanced_rag.py` 或 `backend/app/api/v1/rag.py` |
| Evaluation 模型 | `backend/app/models/evaluation.py` 或分拆为 eval_* 文件 |
| Evaluation 服务 | `backend/app/evaluation/` |
| Evaluation API | `backend/app/api/v1/evaluation.py` |
| Evaluation 前端 | `frontend/src/pages/EvaluationPage.tsx`、`frontend/src/components/evaluation/` |
| 后端测试 | `backend/tests/observability/`、`backend/tests/rag/`、`backend/tests/evaluation/` |
| 项目文档 | `docs/30-trace-observability.md`、`docs/31-trace-timeline.md`、`docs/32-advanced-retrieval.md`、`docs/33-rerank-provider.md`、`docs/34-rag-evaluation.md` |
| 截图 | `docs/assets/plan4/` |

---

## 15. 执行建议

Plan 4 的重点不是堆更多 RAG 技巧，而是让 RAG 系统可观察、可对比、可评测。

推荐实际推进方式：

```text
先做 Trace 基础设施
再把 LLM / RAG 接入 Trace 和 Timeline
再做 Metadata / BM25 / Hybrid
再做 Parent-Child / Query Rewrite
再做 Rerank 和 Strategy Registry
再做 Evaluation 数据集、Runner 和指标
最后补前端页面、测试、文档、截图和 v0.4.0 封版
```

如果时间紧，优先保住：

```text
Trace
RAG 检索记录
Hybrid Search
Rerank Provider
Advanced RAG API
基础 Evaluation 指标
```

Parent-Child、Query Rewrite、LLM-as-Judge 和复杂 Dashboard 可以延期，但延期时必须在 README 和 Plan 4 封版记录里明确说明。
