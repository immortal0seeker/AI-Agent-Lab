# Plan 5 执行步骤表｜核心 Agent Runtime：Memory + State Machine + Long-running Agent

> 适用文档：`00-ALL PLAN/05-PLAN-5 (V1.0).md`  
> 执行方式：每次只领取连续 1～3 个 Step，完成后立即测试、提交、review。  
> 阶段目标：一个阶段完成一个里程碑；一个里程碑通过后再进入下一个里程碑。
> 外部复审策略覆盖（2026-07-18 用户决定）：不再使用 Claude Code；本文件后续所有 Claude Code / Claude review 节点均被此决定覆盖，不作为验收或推进门槛。每批只执行 Codex self-review；全部 6 个 Plan 和整个项目完成后，再由用户决定是否使用 Fable 5 做一次全项目检查。

---

## 0. 执行总原则

| 规则 | 说明 |
|---|---|
| 单次执行范围 | Cursor / Codex 每次只做 1～3 个连续 Step |
| 执行顺序 | 必须按 `P5-Mx-Sy` 顺序推进，除非 Codex 明确记录调整原因 |
| 每步完成定义 | 代码可运行、局部测试通过、相关文档或配置同步 |
| 每个阶段完成定义 | 阶段验收项全部通过，Codex review 后进入下一阶段 |
| Claude Code 使用时机 | Memory 模型、Context Engine、Runtime 状态机、Approval/Recovery、Planner、最终封版前 |
| 提交节奏 | 每 1～3 个 Step 一次 commit；每个里程碑结束一次 review commit |
| 文档同步 | 数据模型、状态枚举、Runtime Policy、审批策略、API 返回结构变化必须同步 docs 或 README |
| 禁止提前做 | MCP Client、语音、视觉、多 Agent、Browser Use / Computer Use、复杂 Workflow Builder、分布式 Worker |

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

## 1. Plan 5 总览

| 阶段 | 里程碑 | 对应原 PLAN5 Step | 核心交付 | 预计时间 | 主要工具 | 审核节点 |
|---|---|---|---|---:|---|---|
| Phase 1 | M1 交接与 Memory 数据底座 | Step 1～8 | v0.4.0 交接检查、Memory ORM/schema、CRUD、Classifier、Dedupe、Sensitivity | 35～45 h | Codex | Codex + Claude Code |
| Phase 2 | M2 Memory Retrieval / Injection / UI | Step 9～11 | Memory 检索、注入、管理页面、写入候选处理 | 20～30 h | Codex + Cursor | Codex review |
| Phase 3 | M3 Context Engine | Step 12～14 | Source Selector、Token Budget、Context Builder、Preview API | 18～28 h | Codex | Codex + Claude Code |
| Phase 4 | M4 Agent Runtime v2 状态机 | Step 15～18 | AgentRun / AgentStep / Event、Runtime Policy、Runtime Service | 28～38 h | Codex | Codex + Claude Code |
| Phase 5 | M5 ReAct + Risk + Human Approval | Step 19～22 | ReAct Agent、Tool Risk Policy、Approval Service、审批 API 与前端卡片 | 28～40 h | Codex + Cursor | Codex + Claude Code |
| Phase 6 | M6 Recovery + Planner + Reflection | Step 23～26 | Retry / Error Recovery、Checkpoint、Pause/Resume、Planner-Executor、Reflection | 34～50 h | Codex | Codex + Claude Code |
| Phase 7 | M7 Agent Runtime API + 前端工作台 + Trace | Step 27～29 | Agent Runtime API、Run 页面、Detail 页面、Trace Timeline 接入 | 32～48 h | Codex + Cursor | Codex + Claude Code |
| Phase 8 | M8 Memory 自动写入 + Context Preview + Agent Evaluation | Step 30～32 | 自动写入闭环、Context Preview 页面、Agent Evaluation 初版 | 26～40 h | Codex + Cursor | Codex + Claude Code |
| Phase 9 | M9 测试、文档与封版 | Step 33～35 | 测试补齐、docs、README、CHANGELOG、截图、v0.5.0 tag | 22～34 h | Codex + Cursor | Codex + Claude final review |

---

## 2. 执行节奏表

| 执行批次 | 建议领取范围 | 批次目标 | 完成后动作 | 状态 |
|---|---|---|---|---|
| Batch 1 | P5-M1-S1～P5-M1-S3 | 确认 Plan4 交接，建立 Memory 数据模型 | 迁移和模型测试 | 未完成 |
| Batch 2 | P5-M1-S4～P5-M1-S6 | 实现 Memory Service / API / Conversation Summary | CRUD 与 summary 测试 | 未完成 |
| Batch 3 | P5-M1-S7～P5-M1-S8 | 实现 Classifier 与 Memory 类型策略 | mock 分类测试 | 未完成 |
| Batch 4 | P5-M1-S9～P5-M1-S10 | 实现 dedupe、sensitivity 与 M1 review | Codex + Claude review M1 | 未完成 |
| Batch 5 | P5-M2-S1～P5-M2-S3 | 实现 Memory Retrieval 与 Retrieval Trace | 检索测试 | 未完成 |
| Batch 6 | P5-M2-S4～P5-M2-S5 | 实现 Memory Injection 与写入决策查询 | 注入测试 | 未完成 |
| Batch 7 | P5-M2-S6～P5-M2-S7 | 实现 Memory 管理页面与 M2 review | 浏览器手测 + Codex review | 未完成 |
| Batch 8 | P5-M3-S1～P5-M3-S3 | 建立 Context Engine 类型、Source Selector、Token Budget | 单元测试 | 未完成 |
| Batch 9 | P5-M3-S4～P5-M3-S6 | 实现 Context Builder、Prompt Sections、Preview API | API 测试 | 未完成 |
| Batch 10 | P5-M3-S7 | 完成 Context Engine 文档与 M3 review | Codex + Claude review M3 | 未完成 |
| Batch 11 | P5-M4-S1～P5-M4-S3 | 设计 Agent Runtime 数据模型与状态枚举 | 迁移和状态测试 | 未完成 |
| Batch 12 | P5-M4-S4～P5-M4-S6 | 实现 Runtime Policy、Event、Step writer | Runtime 单元测试 | 未完成 |
| Batch 13 | P5-M4-S7～P5-M4-S8 | 实现 Agent Runtime Service 与 M4 review | Codex + Claude review M4 | 未完成 |
| Batch 14 | P5-M5-S1～P5-M5-S3 | 实现 ReAct parser、loop、tool observation | ReAct mock 测试 | 未完成 |
| Batch 15 | P5-M5-S4～P5-M5-S5 | 实现 Tool Risk Policy 与 Approval Service | 风险策略测试 | 未完成 |
| Batch 16 | P5-M5-S6～P5-M5-S8 | 实现 Approval API、前端卡片与 M5 review | API + 页面测试，Claude review | 未完成 |
| Batch 17 | P5-M6-S1～P5-M6-S3 | 实现 Retry / Error Recovery | recovery 测试 | 未完成 |
| Batch 18 | P5-M6-S4～P5-M6-S5 | 实现 Checkpoint / Pause / Resume | 恢复测试 | 未完成 |
| Batch 19 | P5-M6-S6～P5-M6-S8 | 实现 Planner-Executor、Reflection 与 M6 review | Codex + Claude review M6 | 未完成 |
| Batch 20 | P5-M7-S1～P5-M7-S3 | 实现 Agent Runtime API | API 测试 | 未完成 |
| Batch 21 | P5-M7-S4～P5-M7-S6 | 实现 Agent Runtime 前端工作台和详情页 | 浏览器手测 | 未完成 |
| Batch 22 | P5-M7-S7～P5-M7-S8 | 接入 Trace Timeline 与 M7 review | Trace 复盘测试，Claude review | 未完成 |
| Batch 23 | P5-M8-S1～P5-M8-S3 | 实现 Memory 自动写入闭环 | 写入决策测试 | 未完成 |
| Batch 24 | P5-M8-S4～P5-M8-S5 | 实现 Context Preview 页面 | 页面手测 | 未完成 |
| Batch 25 | P5-M8-S6～P5-M8-S7 | 实现 Agent Evaluation 初版与 M8 review | Eval 测试，Claude review | 未完成 |
| Batch 26 | P5-M9-S1～P5-M9-S3 | 补齐 Memory / Context / Runtime 测试 | 后端测试 | 未完成 |
| Batch 27 | P5-M9-S4～P5-M9-S5 | 补齐前端验证、README、docs | 页面截图与文档 review | 未完成 |
| Batch 28 | P5-M9-S6～P5-M9-S7 | 全量 review、修复、封版 v0.5.0 | Codex + Claude final review | 未完成 |

---

## 3. Phase 1｜M1 交接与 Memory 数据底座

阶段目标：

```text
确认 v0.4.0 的 Trace、Advanced RAG、Evaluation 可作为 Plan 5 底座，建立 Memory 持久化模型、CRUD 服务、写入判断、去重与敏感信息检查能力。
```

阶段验收：

```text
1. Plan 4 的 TraceRun / TraceStep、Advanced RAG API、RAG Evaluation 至少有可运行证据
2. memories、memory_write_decisions、conversation_summaries 等核心表可用
3. Memory CRUD API 可用
4. Conversation Summary 可生成和查询
5. Memory Classifier、Dedupe、Sensitivity Check 可用 mock 测试验证
6. 所有 Memory 写入决定有 reason、confidence、sensitivity 和 trace / agent 关联字段
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P5-M1-S1 | 检查 Plan 4 封版状态与桥接项 | Codex | Plan 4 交接检查记录 | Trace、Advanced RAG、Evaluation 关键 API 可运行或有明确证据 | Codex |
| P5-M1-S2 | 设计 Memory ORM 与迁移 | Codex | `memories`、`memory_write_decisions`、`conversation_summaries` 等模型 | 迁移和模型测试通过 | Claude Code 可审 |
| P5-M1-S3 | 定义 Memory schema 与枚举 | Codex | `schemas/memory.py`、`memory_types.py` | scope_type、memory_type、status、decision 枚举序列化测试通过 | Codex |
| P5-M1-S4 | 实现 Memory Service | Codex | `memory_service.py` | create、get、list、update、archive/delete 单元测试通过 | Codex |
| P5-M1-S5 | 实现 Memory API | Codex | `api/v1/memories.py` | CRUD API 测试通过，错误返回结构稳定 | Codex |
| P5-M1-S6 | 实现 Conversation Summary 初版 | Codex | `conversation_summary.py` 与 summary API | 长对话 mock 输入可生成 summary 并保存覆盖范围 | Codex |
| P5-M1-S7 | 实现 Memory Classifier | Codex | `memory_classifier.py` | mock LLM 输出可解析为 MemoryCandidate | Claude Code 可审 |
| P5-M1-S8 | 定义 Profile / Project / Episodic / Semantic / Task Memory 策略 | Codex | 类型说明和分类规则 | 不同输入样例被分到预期 memory_type | Codex |
| P5-M1-S9 | 实现 Memory Dedupe 与 Sensitivity Check | Codex | `memory_deduper.py`、`memory_sensitivity.py` | 重复内容、敏感内容、低价值内容均有明确 decision | Claude Code 可审 |
| P5-M1-S10 | 完成 Memory 数据底座文档和 M1 review | Codex | `docs/23-memory-architecture.md` 初版 | 文档说明数据表、写入决策、当前限制 | Codex + Claude review |

M1 完成后建议 commit：

```text
feat(memory): add memory models service and write decisions
```

---

## 4. Phase 2｜M2 Memory Retrieval / Injection / UI

阶段目标：

```text
让 Memory 不只是可保存，还能被检索、被注入上下文、被用户管理，并且能记录每次检索的候选来源和选择原因。
```

阶段验收：

```text
1. Memory Retrieval 可按 scope、type、query、top_k 检索
2. retrieval run 和 candidate 记录可写入
3. Memory Injector 能输出可控 prompt section
4. 用户可在前端查看、搜索、编辑、删除 Memory
5. Memory 写入候选可在前端批准或拒绝
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P5-M2-S1 | 设计 Memory Retrieval run / candidate 模型 | Codex | `memory_retrieval_runs`、`memory_retrieval_candidates` | 迁移和模型测试通过 | Codex |
| P5-M2-S2 | 实现 Memory Retriever | Codex | `memory_retriever.py` | scope、type、top_k、status 过滤测试通过 | Claude Code 可审 |
| P5-M2-S3 | 接入 Memory Retrieval Trace | Codex | retrieval run writer | 检索 query、candidate、score、selected 可查询 | Codex |
| P5-M2-S4 | 实现 Memory Injector | Codex | `memory_injector.py` | 输入 MemorySearchResult 后输出稳定 prompt section | Codex |
| P5-M2-S5 | 实现 Memory 写入决策查询与审批 API | Codex | write-decisions approve/reject API | decision 状态转换测试通过 | Codex |
| P5-M2-S6 | 实现前端 Memory 管理页面 | Cursor | `MemoryPage.tsx` 与 memory components | 可查看、搜索、编辑、归档或删除 Memory | Codex |
| P5-M2-S7 | 实现 MemoryCandidatePanel 与 M2 review | Cursor + Codex | 候选写入审批面板 | 用户可批准或拒绝候选 Memory，文档同步 | Codex review |

M2 完成后建议 commit：

```text
feat(memory): add retrieval injection and management ui
```

---

## 5. Phase 3｜M3 Context Engine

阶段目标：

```text
建立统一 Context Engine，把 System Prompt、Tool Definitions、Memory、RAG、Conversation Summary、Recent Messages、Runtime State 按 token budget 编排成模型输入。
```

阶段验收：

```text
1. ContextBuildRequest / ContextBundle 结构稳定
2. Source Selector 能选择 history、summary、memory、rag、tools、runtime_state
3. Token Budget 能估算、裁剪和记录被裁剪来源
4. Context Builder 能生成 messages 与 sections
5. Context Preview API 可返回模型最终看到的上下文组成
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P5-M3-S1 | 定义 Context Engine 类型 | Codex | `context_types.py` | ContextBuildRequest、ContextSection、ContextBundle schema 测试通过 | Claude Code 可审 |
| P5-M3-S2 | 实现 Source Selector | Codex | `source_selector.py` | 不同 run_mode 下来源选择符合策略 | Codex |
| P5-M3-S3 | 实现 Token Budget | Codex | `token_budget.py` | 超预算时按优先级裁剪，并记录裁剪原因 | Codex |
| P5-M3-S4 | 实现 Prompt Sections | Codex | `prompt_sections.py` | memory、rag、summary、tools section 格式稳定 | Codex |
| P5-M3-S5 | 实现 Context Builder | Codex | `context_builder.py` | mock history + memory + rag 可生成完整 ContextBundle | Claude Code 可审 |
| P5-M3-S6 | 实现 Context Preview API | Codex | `POST /api/v1/context/preview` | API 返回 sections、token_estimate、selected ids、trimmed sources | Codex |
| P5-M3-S7 | 完成 Context Engine 文档和 M3 review | Codex | `docs/24-context-engine.md` | 文档说明来源优先级、预算策略、注入顺序 | Codex + Claude review |

M3 完成后建议 commit：

```text
feat(context): add context engine and preview api
```

---

## 6. Phase 4｜M4 Agent Runtime v2 状态机

阶段目标：

```text
把 Plan 2 的 Simple Agent Loop 升级为可持久化、可观察、可暂停恢复的 Agent Runtime v2 底座。
```

阶段验收：

```text
1. agent_runs、agent_steps、agent_events 或等价结构可用
2. Runtime 状态枚举覆盖 queued、running、waiting_approval、paused、retrying、completed、failed、cancelled
3. Agent Runtime Service 能创建 run、追加 step/event、结束 run、失败 run
4. Runtime Policy 能控制 max_steps、max_retries、allowed_tools、risk limits
5. Runtime 与 Plan 4 Trace 之间保留明确关联
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P5-M4-S1 | 设计 Agent Runtime ORM 与迁移 | Codex | `agent_runs`、`agent_steps`、`agent_events` 或等价模型 | 迁移和模型测试通过 | Claude Code 可审 |
| P5-M4-S2 | 定义 Runtime State 与 Step Type | Codex | `runtime_state.py`、`runtime_events.py` | 状态转换枚举测试通过 | Codex |
| P5-M4-S3 | 定义 Runtime schema | Codex | `schemas/agent_runtime.py` | AgentRun、AgentStep、AgentEvent 返回结构稳定 | Codex |
| P5-M4-S4 | 实现 Runtime Policy | Codex | `runtime_policy.py` | max_steps、allowed_tools、approval_required、retry 策略测试通过 | Claude Code 可审 |
| P5-M4-S5 | 实现 Runtime Event 与 Step writer | Codex | step/event 写入服务 | 每个 step 可记录 input、output、status、error、trace_step_id | Codex |
| P5-M4-S6 | 实现 Agent Runtime Service 核心生命周期 | Codex | `agent_runtime.py` | create_run、start_run、complete_run、fail_run 测试通过 | Codex |
| P5-M4-S7 | 接入 Context Engine 到 Runtime | Codex | build_context step | Agent Run 启动时生成 context_snapshot | Codex |
| P5-M4-S8 | 完成 Runtime 状态机文档和 M4 review | Codex | `docs/25-agent-runtime-state-machine.md` | 文档说明状态图、step 生命周期、policy 字段 | Codex + Claude review |

M4 完成后建议 commit：

```text
feat(agent): add runtime state machine
```

---

## 7. Phase 5｜M5 ReAct + Risk + Human Approval

阶段目标：

```text
在 Runtime v2 上实现 ReAct Agent，并让高风险工具调用在执行前进入 Human Approval 流程。
```

阶段验收：

```text
1. ReAct parser 能解析 Thought / Action / Action Input / Observation / Final Answer
2. ReAct loop 能通过 Tool Registry 调用允许的工具
3. Tool Risk Policy 能区分 read、write、external、destructive 等风险等级
4. 高风险动作创建 approval_requests，并让 Agent Run 进入 waiting_approval
5. 用户批准后继续执行，拒绝后按 policy 结束或改写计划
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P5-M5-S1 | 实现 ReAct parser | Codex | `react_agent.py` parser | 标准 ReAct 文本和 JSON 输入解析测试通过 | Codex |
| P5-M5-S2 | 实现 ReAct Agent loop | Codex | ReAct runtime pattern | mock LLM + mock tool 可跑完 Thought / Action / Observation | Claude Code 可审 |
| P5-M5-S3 | 将 ReAct step 写入 Runtime 与 Trace | Codex | thought/action/observation/final_answer step | Agent Run Detail 可查询完整 step | Codex |
| P5-M5-S4 | 实现 Tool Risk Policy | Codex | `risk_policy.py` | read/write/external/destructive 工具风险判定测试通过 | Claude Code 可审 |
| P5-M5-S5 | 实现 Approval Service | Codex | `approval_service.py` | create、approve、reject、expire 状态转换测试通过 | Codex |
| P5-M5-S6 | 实现 Approval API | Codex | `api/v1/agent_approvals.py` | pending approval 可查询、批准、拒绝 | Codex |
| P5-M5-S7 | 实现前端 ApprovalRequestCard | Cursor | approval card component | Agent Run Detail 中可批准或拒绝一次动作 | Codex |
| P5-M5-S8 | 完成 Human Approval 文档和 M5 review | Codex | `docs/28-human-approval-and-recovery.md` 初版 | 文档说明风险等级、审批状态、拒绝后的行为 | Codex + Claude review |

M5 完成后建议 commit：

```text
feat(agent): add react agent and human approval
```

---

## 8. Phase 6｜M6 Recovery + Planner + Reflection

阶段目标：

```text
让 Agent Run 能处理常见失败、保存 checkpoint、暂停恢复，并支持 Planner-Executor 与轻量 Reflection。
```

阶段验收：

```text
1. 可恢复错误会按策略 retry，权限拒绝和审批拒绝不会盲目重试
2. 每个重要 step 后可保存 checkpoint
3. pause / resume / cancel 能改变 run 状态并保持可查询
4. Planner-Executor 可生成 plan items，并按 item 关联 agent_step
5. Reflection 可在最终回答前记录自检结果
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P5-M6-S1 | 定义 Error Recovery 类型与策略 | Codex | `recovery.py` error types | timeout、rate_limit、tool_validation、permission_denied 分类测试通过 | Claude Code 可审 |
| P5-M6-S2 | 实现 Retry 机制 | Codex | retry handler | 可恢复错误递增 retry_count，达到 max_retries 后 fail step | Codex |
| P5-M6-S3 | 接入 Recovery Trace | Codex | retry/error trace step | Trace 中可看到 error_type、retry_count、final status | Codex |
| P5-M6-S4 | 实现 Checkpoint Service | Codex | `checkpoint_service.py` | step 边界可保存 state_json 与 context_snapshot | Claude Code 可审 |
| P5-M6-S5 | 实现 Pause / Resume / Cancel | Codex | runtime lifecycle 方法 | paused 后不继续执行，resume 后从最近 checkpoint 继续 | Codex |
| P5-M6-S6 | 实现 Planner-Executor | Codex | `planner_executor.py` | mock planner 输出 3～8 个 plan item 并逐项执行 | Claude Code 可审 |
| P5-M6-S7 | 实现 Reflection | Codex | `reflection.py` | 最终回答前可生成 passed/issues/revised_answer 记录 | Codex |
| P5-M6-S8 | 完成 Planner / Recovery 文档和 M6 review | Codex | `docs/27-planner-executor.md`、`docs/28-human-approval-and-recovery.md` 更新 | 文档说明恢复边界、planner 限制、reflection 输出 | Codex + Claude review |

M6 完成后建议 commit：

```text
feat(agent): add recovery checkpoint planner and reflection
```

---

## 9. Phase 7｜M7 Agent Runtime API + 前端工作台 + Trace

阶段目标：

```text
把 Runtime 能力暴露给前端，让用户可以创建、观察、暂停、恢复、取消、重试 Agent Run，并在 Trace Timeline 中复盘完整执行过程。
```

阶段验收：

```text
1. Agent Runtime API 可创建和查询 run、steps、events、plan
2. pause / resume / cancel / retry API 可用
3. 前端可创建 ReAct 或 Planner-Executor run
4. Agent Run Detail 可展示 Plan Tree、Step Timeline、Thought / Action / Observation、Approval、Recovery
5. Agent Run 可跳转到 Trace Timeline
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P5-M7-S1 | 实现 Agent Runtime API 基础查询 | Codex | `api/v1/agent_runs.py` | POST / GET run、steps、events、plan 测试通过 | Codex |
| P5-M7-S2 | 实现 Agent Runtime 控制 API | Codex | pause/resume/cancel/retry endpoints | 状态转换和错误返回测试通过 | Codex |
| P5-M7-S3 | 补齐 Agent Runtime API 文档 | Codex | OpenAPI 说明或 docs | API 参数、状态、错误码说明清楚 | Codex |
| P5-M7-S4 | 实现前端 Agent Runtime API 封装与类型 | Cursor | `agentRuns.ts`、`agentRuntime.ts` | TypeScript 检查通过 | Codex |
| P5-M7-S5 | 实现 AgentRuntimePage | Cursor | run 创建表单、run 列表、mode/policy 配置 | 浏览器可创建并查看 run | Codex |
| P5-M7-S6 | 实现 AgentRunDetailPage | Cursor + Codex | Plan Tree、Step Timeline、TAO 展示、控制按钮 | 页面可展示运行中的 step 与最终结果 | Codex |
| P5-M7-S7 | 接入 Plan 4 Trace Timeline | Codex | Agent Run trace_run_id 与跳转链接 | 一次 Agent Run 可在 Trace 页面复盘 | Claude Code 可审 |
| P5-M7-S8 | 完成 Agent Runtime UI review | Codex + Cursor | 手测记录与截图清单 | 页面状态、错误态、waiting approval 态均可验证 | Codex + Claude review |

M7 完成后建议 commit：

```text
feat(frontend): add agent runtime workspace
```

---

## 10. Phase 8｜M8 Memory 自动写入 + Context Preview + Agent Evaluation

阶段目标：

```text
闭合 Agent Run 结束后的 Memory 写入链路，提供 Context Preview 调试页面，并建立 Agent Evaluation 初版。
```

阶段验收：

```text
1. Agent Run 完成后可生成 MemoryCandidate
2. 自动写入只发生在低风险、高置信度、非重复内容上
3. 需要用户确认的候选会进入 MemoryCandidatePanel
4. Context Preview 页面可展示模型最终上下文组成
5. Agent Evaluation 可用小型测试集评估任务成功、工具命中、审批合规、成本和延迟
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P5-M8-S1 | 实现 Agent Run 结束后的 Memory Candidate 生成 | Codex | auto-write hook | 完成 run 后生成候选并关联 agent_run_id | Codex |
| P5-M8-S2 | 实现自动写入策略 | Codex | confidence / sensitivity / duplicate policy | 低风险高置信度写入，高风险进入审批 | Claude Code 可审 |
| P5-M8-S3 | 接入 MemoryCandidatePanel | Cursor + Codex | 候选列表、批准、拒绝 | 用户可处理自动写入候选 | Codex |
| P5-M8-S4 | 实现 Context Preview 前端页面 | Cursor | `ContextPreview.tsx` 与 context components | 可查看 system、memory、rag、summary、token budget | Codex |
| P5-M8-S5 | 完成 Context Preview 手测与文档 | Codex + Cursor | 手测记录、截图、docs 更新 | 页面能解释被裁剪来源和选中来源 | Codex |
| P5-M8-S6 | 实现 Agent Evaluation 初版 | Codex | `agent_eval_types.py`、`agent_eval_runner.py`、`agent_metrics.py` | mock tool 测试集可运行并输出指标 | Claude Code 可审 |
| P5-M8-S7 | 实现 Agent Evaluation API 与 M8 review | Codex | eval datasets/runs/results API | 可创建测试集、运行 eval、查询结果 | Codex + Claude review |

M8 完成后建议 commit：

```text
feat(evaluation): add agent runtime evaluation
```

---

## 11. Phase 9｜M9 测试、文档与封版

阶段目标：

```text
补齐 Plan 5 的测试、文档、截图、变更记录和封版检查，确保 v0.5.0 可以作为 Plan 6 的稳定底座。
```

阶段验收：

```text
1. Memory、Context Engine、Runtime、ReAct、Approval、Recovery、Planner、Evaluation 核心测试通过
2. 前端主要页面有手测记录或截图
3. README、CHANGELOG、docs 覆盖 v0.5.0 能力、限制和启动方式
4. Plan 5 到 Plan 6 的桥接检查全部通过
5. v0.5.0 tag 创建前经过 Codex + Claude final review
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P5-M9-S1 | 补齐 Memory 与 Context Engine 测试 | Codex | memory/context tests | CRUD、retrieval、injection、token budget、context builder 测试通过 | Codex |
| P5-M9-S2 | 补齐 Runtime 与 Agent pattern 测试 | Codex | runtime/react/planner tests | state transition、ReAct、planner、reflection 测试通过 | Claude Code 可审 |
| P5-M9-S3 | 补齐 Approval / Recovery / Checkpoint 测试 | Codex | approval/recovery/checkpoint tests | 审批、retry、pause/resume/cancel 测试通过 | Codex |
| P5-M9-S4 | 补齐前端页面验证与截图 | Cursor + Codex | Memory、Agent Runtime、Run Detail、Approval、Context Preview 截图 | 浏览器手测记录齐全 | Codex |
| P5-M9-S5 | 更新 README、docs、CHANGELOG | Codex | v0.5.0 文档和版本记录 | 文档覆盖 Memory、Context、Runtime、Approval、Recovery、Evaluation | Codex |
| P5-M9-S6 | 执行 Plan 5 全量 review 与修复 | Codex + Claude Code | review 记录、修复 commit | 全量测试通过，关键风险有处理结论 | Codex + Claude final review |
| P5-M9-S7 | 完成 v0.5.0 封版 | Codex | tag、截图、验收清单 | `git tag --list` 可见 v0.5.0，Plan 6 桥接项通过 | Codex |

M9 完成后建议 commit：

```text
chore: release v0.5.0 agent runtime
```

---

## 12. 每次执行 1～3 步的标准流程

每次让 Codex / Cursor 执行时，建议按这个模板下发：

```text
当前执行范围：P5-Mx-Sy ～ P5-Mx-Sz

必须遵守：
1. 只做这些 Step，不提前做 MCP、语音、视觉、多 Agent、Browser Use 或复杂 Workflow Builder。
2. 保持 Plan 1～4 已有 Chat、Tool、RAG、Trace、Evaluation 能力兼容。
3. 任何状态枚举、API 返回结构、数据库字段变化都要同步测试和文档。

完成要求：
1. 实现对应交付物。
2. 跑对应验证命令。
3. 修复发现的问题。
4. 更新必要文档。
5. 给出变更摘要、测试结果和下一批建议。
```

执行完成后，Codex review 使用这个检查表：

```text
1. 是否只修改了本批次相关文件
2. 是否破坏 Plan 4 Trace / RAG / Evaluation 既有能力
3. Memory 是否可审计、可删除、可解释写入原因
4. Context Engine 是否能说明每个上下文来源和裁剪原因
5. Runtime 状态转换是否单向清晰，失败状态是否可复盘
6. Tool Risk Policy 是否能保护写入、外部调用和潜在破坏性动作
7. Human Approval 是否不会被 retry 或 resume 绕过
8. Retry 是否只处理可恢复错误
9. Checkpoint / Resume 是否只在明确 step 边界恢复
10. Trace 是否覆盖 build_context、memory_retrieve、plan、action、approval、retry、reflection、final_answer
11. README / docs / env example 是否同步
12. 是否适合进入下一批次
```

---

## 13. Claude Code Review 节点

Claude Code 不需要每个 Step 都参与，建议在这些节点使用：

| 节点 | 审核重点 | 输入材料 |
|---|---|---|
| M1 结束 | Memory 数据模型、写入决策、去重、敏感信息检查是否安全可审计 | diff、ORM、schema、Memory Service、测试结果 |
| M3 结束 | Context Engine 是否能稳定编排 Memory / RAG / History / Runtime State | diff、Context Builder、Token Budget、Preview API、测试结果 |
| M4 结束 | Runtime 状态机是否清晰，状态转换是否能支撑 pause/resume/retry/approval | diff、runtime_state、agent_runtime、policy、测试结果 |
| M5 结束 | ReAct + Approval 是否存在绕过风险，高风险动作是否必须审批 | diff、risk policy、approval service、API、前端卡片、测试结果 |
| M6 结束 | Recovery、Checkpoint、Planner、Reflection 是否形成可恢复闭环 | diff、recovery、checkpoint、planner、reflection、测试结果 |
| M8 结束 | Memory 自动写入和 Agent Evaluation 是否可控、可解释、可复测 | diff、auto-write hook、eval runner、metrics、测试集 |
| M9 封版前 | v0.5.0 是否能作为 Plan 6 MCP / Voice / Vision / Desktop 的稳定 Runtime 底座 | 全量 diff、README、测试结果、截图、CHANGELOG、桥接检查 |

Claude Code 审核后，Codex 负责：

```text
1. 判断哪些意见必须修
2. 拆成 1～3 个修复 Step
3. 修复后重新跑测试
4. 更新文档和 changelog
5. 记录是否允许进入下一阶段
```

---

## 14. Plan 5 最终验收清单

| 验收项 | 状态 | 证据 |
|---|---|---|
| memories 表可用 | pending | ORM / migration / test |
| memory_write_decisions 表可用 | pending | ORM / migration / test |
| memory_retrieval_runs / candidates 可用 | pending | retrieval trace test |
| conversation_summaries 可用 | pending | summary test |
| Memory CRUD API 可用 | pending | API test |
| Memory Classifier 可用 | pending | mock classifier test |
| Memory Dedupe 可用 | pending | duplicate test |
| Memory Sensitivity Check 可用 | pending | sensitivity test |
| Memory Retrieval 可用 | pending | retrieval test |
| Memory Injection 可用 | pending | prompt section test |
| Memory 管理页面可用 | pending | 页面截图 |
| Context Engine 数据结构完成 | pending | schema test |
| Token Budget 可用 | pending | budget test |
| Context Builder 可用 | pending | context bundle test |
| Context Preview API 可用 | pending | API test |
| Context Preview 页面可用 | pending | 页面截图 |
| AgentRun / AgentStep / AgentEvent 可用 | pending | ORM / schema / test |
| Runtime State Machine 可用 | pending | state transition test |
| Runtime Policy 可用 | pending | policy test |
| ReAct Agent 可用 | pending | mock agent run |
| Tool Risk Policy 可用 | pending | risk policy test |
| Human Approval 可用 | pending | approval test |
| Approval API 可用 | pending | API test |
| Approval 前端卡片可用 | pending | 页面截图 |
| Retry / Error Recovery 可用 | pending | recovery test |
| Checkpoint / Pause / Resume 可用 | pending | resume test |
| Planner-Executor 可用 | pending | planner test |
| Reflection 可用 | pending | reflection test |
| Agent Runtime API 可用 | pending | API test |
| Agent Runtime 前端页面可用 | pending | 页面截图 |
| Agent Run 写入 Trace Timeline | pending | trace run evidence |
| Memory 自动写入闭环可用 | pending | candidate decision test |
| Agent Evaluation 初版可用 | pending | eval run evidence |
| 核心测试已补齐 | pending | test output |
| README 已更新 | pending | README link |
| docs 已更新 | pending | docs links |
| CHANGELOG 已更新 | pending | changelog link |
| 已创建 v0.5.0 tag | pending | `git tag --list` 输出 |

---

## 15. Plan 5 到 Plan 6 的桥接检查

只有下面 6 项都满足，才建议进入 Plan 6：

| 桥接项 | 状态 | 说明 |
|---|---|---|
| Tool Risk Policy 能覆盖内置工具和外部工具 | pending | MCP Tool Call 进入后复用同一套风险等级 |
| Human Approval API 可被 MCP Tool Call 复用 | pending | Plan 6 不需要重新设计审批机制 |
| Agent Runtime 支持动态工具注册 | pending | MCP 工具进入 Tool Registry 后不需要重写执行循环 |
| Agent Run Detail 能展示 Tool Call、Approval、Trace 三类事件 | pending | Plan 6 的外部工具调用可直接复盘 |
| Checkpoint / Resume 支持 paused、running、completed、failed、cancelled 状态恢复 | pending | 长任务和桌面端刷新后可恢复 |
| Context Engine 能注入 Memory、RAG、Tool Definitions、Runtime State | pending | Plan 6 的 MCP、Voice、Vision 都共享上下文底座 |

---

## 16. 推荐文件位置

执行过程中建议把相关产物放在这些位置：

| 类型 | 路径 |
|---|---|
| Memory 类型与服务 | `backend/app/memory/` |
| Memory ORM | `backend/app/models/memory.py` |
| Memory schema | `backend/app/schemas/memory.py` |
| Memory API | `backend/app/api/v1/memories.py` |
| Context Engine | `backend/app/context_engine/` |
| Context Preview API | `backend/app/api/v1/context.py` |
| Agent Runtime | `backend/app/agents/runtime/` |
| ReAct / Planner / Reflection | `backend/app/agents/patterns/` |
| Approval / Risk Policy | `backend/app/agents/approval/` |
| Agent Evaluation | `backend/app/agents/evaluation/` |
| Agent Runtime ORM | `backend/app/models/agent_runtime.py` |
| Approval ORM | `backend/app/models/approval.py` |
| Agent Runtime schema | `backend/app/schemas/agent_runtime.py` |
| Approval schema | `backend/app/schemas/approval.py` |
| Agent Runtime API | `backend/app/api/v1/agent_runs.py` |
| Approval API | `backend/app/api/v1/agent_approvals.py` |
| Agent Evaluation API | `backend/app/api/v1/agent_evaluations.py` |
| Memory 前端 | `frontend/src/pages/MemoryPage.tsx`、`frontend/src/components/memory/` |
| Agent Runtime 前端 | `frontend/src/pages/AgentRuntimePage.tsx`、`frontend/src/pages/AgentRunDetailPage.tsx`、`frontend/src/components/agent/` |
| Context Preview 前端 | `frontend/src/components/context/`、`frontend/src/pages/ContextPreviewPage.tsx` |
| 前端 API 封装 | `frontend/src/api/memories.ts`、`frontend/src/api/agentRuns.ts`、`frontend/src/api/agentApprovals.ts` |
| 后端测试 | `backend/tests/memory/`、`backend/tests/context_engine/`、`backend/tests/agents/` |
| 前端验证记录 | `docs/assets/plan5/` |
| 项目文档 | `docs/23-memory-architecture.md`、`docs/24-context-engine.md`、`docs/25-agent-runtime-state-machine.md`、`docs/26-react-agent.md`、`docs/27-planner-executor.md`、`docs/28-human-approval-and-recovery.md`、`docs/29-agent-evaluation.md` |

---

## 17. 执行建议

Plan 5 是整个项目从“AI 应用工作台”进入“Agent 工程运行时”的关键阶段。推进时不要把重点放在让模型显得更聪明，而要把重点放在这些工程能力上：

```text
可管理的 Memory
可解释的上下文
可持久化的 Agent Run
可复盘的 Step / Event / Trace
可审批的高风险动作
可恢复的失败处理
可验证的 Agent Evaluation
```

推荐实际推进方式：

```text
先做 Memory 可管理
再做 Context Engine
再做 Runtime 状态机
再做 ReAct
再做 Human Approval
再做 Recovery / Checkpoint
再做 Planner / Reflection
再做前端工作台和 Trace 复盘
最后补 Evaluation、测试、文档和封版
```

如果时间紧，优先保住：

```text
Memory CRUD
Memory Retrieval / Injection
Context Builder
Runtime State Machine
ReAct Agent
Tool Risk Policy
Human Approval
Agent Runtime API
Agent Run Detail
Trace 接入
README 和核心测试
```

Planner-Executor 的完整 UI、Reflection 的复杂策略、Agent Evaluation 的多指标 dashboard、异步 Worker 和更复杂的 Checkpoint 恢复都可以在 v0.5.x 继续增强；但 Runtime 状态机、Human Approval 和 Trace 接入不能省略，否则 Plan 6 的 MCP 和桌面端会缺少安全底座。
