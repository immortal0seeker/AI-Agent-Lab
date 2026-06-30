# Plan 5｜核心 Agent Runtime：Memory + State Machine + Long-running Agent

## 0. 子计划定位

Plan 5 对应项目总路线中的：

```text
Plan 5：核心 Agent Runtime
对应阶段口径：Phase 6 Memory + Agent Runtime 强化
```

Plan 5 的前置条件是：

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

Plan 4 已完成
版本：v0.4.0
成果：Trace + Advanced RAG + Rerank + Evaluation 可运行
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

- Naive RAG

- Advanced RAG

- Hybrid Search

- Rerank

- RAG Evaluation

- Trace Run / Trace Step

- Timeline 页面

- Token / Cost / Latency 可观测

Plan 5 不重写 Plan 1～Plan 4 的能力。

Plan 5 的目标是在这些能力之上构建真正的 Agent Runtime：

> Memory、Context Engine、状态机、ReAct、Planner-Executor、Reflection、Human Approval、Retry / Error Recovery、Checkpoint / Resume、Long-running Agent Run。

Plan 5 的重点不是让 Agent 多几个工具，而是让 Agent 从“能循环调用工具的 Demo”升级为：

> 能记住背景、能规划任务、能按状态执行、能被观察、能暂停恢复、能在高风险动作前请求确认的工程化 Agent Runtime。

---

## 1. Plan 5 核心目标

Plan 5 的核心目标是：

> 把 Plan 2 的 Simple Agent Loop 升级为可长期演进的 Agent Runtime，把 Plan 4 的 Trace 能力接入 Agent 执行全过程，并引入 Memory 作为上下文工程的重要来源。

完成 Plan 5 后，系统应该支持：

```text
用户发起一个多步任务
    -> 系统创建 agent_run
    -> 构建上下文
    -> 检索相关 Memory
    -> 可选检索 RAG 知识库
    -> Planner 生成任务计划
    -> Agent 按 step 执行
    -> ReAct 循环产生 Thought / Action / Observation
    -> 工具调用前检查权限和风险
    -> 高风险步骤创建 Human Approval
    -> 用户批准或拒绝
    -> Runtime 根据结果继续、回退或结束
    -> 出错时按策略 retry / fallback
    -> 每个步骤写入 Trace
    -> 关键事实经过 Memory Classifier 判断后写入 Memory
    -> 最终输出答案、执行摘要、计划完成情况和可追踪 Timeline
```

典型验收场景：

```text
用户说：
请分析这个项目的 RAG 模块，并给我一份优化计划。

系统应该可以：
1. 读取用户偏好和项目记忆
2. 识别这是一个多步任务
3. 生成计划：
   - 查找 RAG 相关文件
   - 读取核心实现
   - 总结当前架构
   - 找出问题
   - 给出优化计划
4. 按步骤执行工具调用
5. 在需要写文件或执行命令前请求确认
6. 出错时重试或给出可恢复状态
7. 在前端展示计划、步骤、工具结果、Trace、成本和最终报告
8. 把稳定的项目事实写入 Project Memory
```

Plan 5 的成果不是一个新的聊天页面，而是：

> Agent Runtime 中枢：Memory 管理、上下文构造、状态执行、审批控制、错误恢复、长期任务运行。

---

## 2. Plan 5 不做什么

为了控制范围，Plan 5 暂时不做：

| 暂不做 | 原因 |
| --- | --- |
| MCP Client | 放到 Plan 6，Plan 5 只保证 Runtime 可以接入更多工具 |
| 语音输入 / TTS | 放到 Plan 6 或后续产品化阶段 |
| 图片 / OCR / VLM | 放到多模态阶段 |
| Electron / Tauri 桌面端 | 放到 Plan 6 |
| 多 Agent 协作 | 放到后期扩展，Plan 5 先做好单 Agent Runtime |
| GraphRAG | 与 Agent Runtime 主线不同，后期研究 |
| Browser Use / Computer Use | 工具风险高，先不进入 v0.5.0 |
| 自动代码修改 Agent | 依赖更强权限系统和审批机制，Plan 5 只打基础 |
| 复杂可视化 Workflow Builder | 本阶段做运行时状态机，不做拖拽编排器 |
| 分布式 Agent Worker 集群 | 初版可以同步或轻量后台执行，先保证模型清晰 |
| 多用户权限系统 | 保持单用户学习项目边界 |
| 完整商业级 Memory 治理 | 初版做可查看、可编辑、可删除、可审计 |

Plan 5 只做：

> Memory + Context Engine + Agent Runtime v2 + Human Approval + Recovery 的可运行闭环。

---

## 3. Plan 5 版本目标

| 项目 | 内容 |
| --- | --- |
| 子计划名称 | Plan 5：核心 Agent Runtime |
| 对应范围 | Memory + Agent Runtime 强化 |
| 对应 Phase | Phase 6 |
| 起始版本 | v0.4.0 |
| 目标版本 | v0.5.0 |
| 核心能力 | 长期记忆、多步 Agent、状态机、审批、恢复 |
| 预计时间 | 120～180 小时 |
| 难度 | 高 |
| 项目价值 | 把项目从“AI 应用工作台”提升到“Agent 工程运行时” |

---

## 4. Plan 5 技术重点

Plan 5 重点学习和实现：

- Memory Architecture

- Conversation Summary

- Profile Memory

- Project Memory

- Episodic Memory

- Semantic Memory

- Task Memory

- Memory Classifier

- Memory Deduplication

- Memory Sensitivity Check

- Memory Retrieval

- Memory Injection

- Context Engine

- Token Budget

- Agent Runtime State Machine

- Agent Run / Step / Event

- Runtime Policy

- ReAct Agent

- Planner-Executor

- Reflection

- Human Approval

- Retry Policy

- Error Recovery

- Checkpoint / Resume

- Long-running Agent Run

- Agent Trace Integration

- Agent Evaluation

---

## 5. Plan 5 推荐里程碑拆分

| 里程碑 | 名称 | 内容 | 预计时间 |
| --- | --- | --- | --- |
| M1 | Memory 基础设施 | Memory 数据模型、CRUD、Classifier、检索、注入、管理页面 | 35～55 h |
| M2 | Context Engine | 上下文来源编排、Token 预算、Memory / RAG / History 注入 | 18～28 h |
| M3 | Agent Runtime v2 | Run / Step / Event、状态机、ReAct、Trace 接入 | 30～45 h |
| M4 | Planner + Approval + Recovery | Planner-Executor、Human Approval、Retry、Checkpoint / Resume | 30～45 h |
| M5 | UI + Evaluation + 封版 | Agent 工作台页面、Agent Eval、测试、文档、v0.5.0 | 25～40 h |

Plan 5 的风险点是概念容易膨胀。

推荐优先级：

```text
必须完成：
Memory CRUD、Memory 写入判断、Memory 检索注入、Context Engine、Agent 状态机、ReAct、Human Approval、Trace 接入

尽量完成：
Planner-Executor、Reflection、Checkpoint / Resume、Agent Evaluation、Memory 管理页面体验优化

可以延期：
复杂任务队列、异步 Worker、复杂 Workflow Builder、多 Agent、Browser Use、Computer Use
```

---

## 6. Plan 5 推荐目录结构调整

在 Plan 4 基础上，后端新增或强化：

```text
backend/app/
├── memory/
│   ├── memory_types.py
│   ├── memory_service.py
│   ├── memory_classifier.py
│   ├── memory_retriever.py
│   ├── memory_deduper.py
│   ├── memory_sensitivity.py
│   ├── memory_injector.py
│   └── conversation_summary.py
├── context_engine/
│   ├── context_types.py
│   ├── context_builder.py
│   ├── token_budget.py
│   ├── source_selector.py
│   └── prompt_sections.py
├── agents/
│   ├── runtime/
│   │   ├── agent_runtime.py
│   │   ├── runtime_state.py
│   │   ├── runtime_policy.py
│   │   ├── runtime_events.py
│   │   ├── checkpoint_service.py
│   │   └── recovery.py
│   ├── patterns/
│   │   ├── react_agent.py
│   │   ├── planner_executor.py
│   │   └── reflection.py
│   ├── approval/
│   │   ├── approval_service.py
│   │   └── risk_policy.py
│   └── evaluation/
│       ├── agent_eval_types.py
│       ├── agent_eval_runner.py
│       └── agent_metrics.py
├── models/
│   ├── memory.py
│   ├── agent_runtime.py
│   ├── approval.py
│   └── agent_evaluation.py
├── schemas/
│   ├── memory.py
│   ├── agent_runtime.py
│   ├── approval.py
│   └── agent_evaluation.py
└── api/v1/
    ├── memories.py
    ├── agent_runs.py
    ├── agent_approvals.py
    └── agent_evaluations.py
```

前端新增或强化：

```text
frontend/src/
├── pages/
│   ├── MemoryPage.tsx
│   ├── AgentRuntimePage.tsx
│   └── AgentRunDetailPage.tsx
├── components/
│   ├── memory/
│   │   ├── MemoryList.tsx
│   │   ├── MemoryEditor.tsx
│   │   ├── MemoryCandidatePanel.tsx
│   │   ├── MemorySourceBadge.tsx
│   │   └── MemorySearchPanel.tsx
│   ├── agent/
│   │   ├── AgentRunPanel.tsx
│   │   ├── AgentPlanTree.tsx
│   │   ├── AgentStepTimeline.tsx
│   │   ├── ThoughtActionObservation.tsx
│   │   ├── ApprovalRequestCard.tsx
│   │   ├── RuntimeStateBadge.tsx
│   │   └── RecoveryPanel.tsx
│   └── context/
│       ├── ContextPreview.tsx
│       ├── TokenBudgetBar.tsx
│       └── ContextSourceList.tsx
├── api/
│   ├── memories.ts
│   ├── agentRuns.ts
│   ├── agentApprovals.ts
│   └── agentEvaluations.ts
└── types/
    ├── memory.ts
    ├── agentRuntime.ts
    ├── approval.ts
    └── context.ts
```

说明：

```text
如果 Plan 2 已经存在 agents/ 或 agent_runs 表，Plan 5 优先扩展已有结构。
不要为了目录漂亮而重写已经能工作的 Tool Registry 和 Simple Agent Loop。
```

---

## 7. Plan 5 数据库设计

### 7.1 memories

用于保存长期可复用的记忆。

```sql
memories
- id
- scope_type
- scope_id
- memory_type
- title
- content
- structured_json
- importance
- confidence
- sensitivity
- status
- source_type
- source_id
- vector_id
- last_used_at
- created_at
- updated_at
```

`scope_type` 建议：

```text
user
project
conversation
global
```

`memory_type` 建议：

```text
profile
project
episodic
semantic
preference
task
conversation_summary
```

`status` 建议：

```text
active
archived
deleted
```

---

### 7.2 memory_write_decisions

用于记录“为什么写入或不写入记忆”。

```sql
memory_write_decisions
- id
- trace_run_id
- agent_run_id
- conversation_id
- message_id
- candidate_content
- proposed_memory_type
- decision
- reason
- importance
- confidence
- sensitivity
- duplicate_memory_id
- requires_user_approval
- approved_by_user
- created_memory_id
- created_at
```

`decision` 建议：

```text
write
skip_low_value
skip_duplicate
skip_sensitive
needs_approval
merge_existing
```

---

### 7.3 memory_retrieval_runs

用于记录一次 Memory 检索。

```sql
memory_retrieval_runs
- id
- trace_run_id
- agent_run_id
- query
- scope_type
- scope_id
- memory_types_json
- top_k
- latency_ms
- created_at
```

---

### 7.4 memory_retrieval_candidates

用于记录 Memory 检索候选。

```sql
memory_retrieval_candidates
- id
- retrieval_run_id
- memory_id
- rank
- score
- selected
- reason
- created_at
```

---

### 7.5 conversation_summaries

用于保存滚动会话摘要。

```sql
conversation_summaries
- id
- conversation_id
- summary_text
- covered_message_start_id
- covered_message_end_id
- token_count
- created_by_model
- created_at
```

---

### 7.6 agent_runs

如果 Plan 2 已经有 `agent_runs`，本阶段扩展字段。

```sql
agent_runs
- id
- conversation_id
- trace_run_id
- run_mode
- goal
- input_text
- final_output
- status
- current_step_index
- max_steps
- runtime_policy_json
- context_snapshot_json
- error_message
- started_at
- ended_at
- created_at
- updated_at
```

`run_mode` 建议：

```text
single_turn
tool_using
react
planner_executor
reflection
```

`status` 建议：

```text
queued
running
waiting_approval
paused
retrying
completed
failed
cancelled
```

---

### 7.7 agent_steps

如果 Plan 2 已经有 `agent_steps`，本阶段扩展为 Runtime Step。

```sql
agent_steps
- id
- agent_run_id
- trace_step_id
- step_index
- step_type
- title
- thought
- action_name
- action_input_json
- observation
- output_json
- status
- retry_count
- error_message
- started_at
- ended_at
- created_at
```

`step_type` 建议：

```text
build_context
memory_retrieve
plan
thought
action
tool_call
observation
approval
reflection
final_answer
```

---

### 7.8 agent_plans

用于保存 Planner 生成的计划。

```sql
agent_plans
- id
- agent_run_id
- goal
- plan_text
- status
- created_at
- updated_at
```

---

### 7.9 agent_plan_items

用于保存计划中的每个步骤。

```sql
agent_plan_items
- id
- agent_plan_id
- item_index
- title
- description
- status
- linked_agent_step_id
- created_at
- updated_at
```

`status` 建议：

```text
pending
running
completed
failed
skipped
```

---

### 7.10 approval_requests

用于记录需要用户确认的高风险动作。

```sql
approval_requests
- id
- agent_run_id
- agent_step_id
- risk_level
- action_name
- action_input_json
- reason
- status
- requested_at
- decided_at
- decision_by
- decision_note
```

`status` 建议：

```text
pending
approved
rejected
expired
cancelled
```

---

### 7.11 agent_checkpoints

用于保存可恢复状态。

```sql
agent_checkpoints
- id
- agent_run_id
- step_index
- state_json
- context_snapshot_json
- created_at
```

---

### 7.12 agent_eval_cases

用于评测 Agent 多步任务能力。

```sql
agent_eval_cases
- id
- dataset_id
- name
- user_task
- expected_tools_json
- expected_keywords_json
- forbidden_actions_json
- success_criteria_json
- created_at
```

---

## 8. Plan 5 核心接口设计

### 8.1 Memory API

```text
POST /api/v1/memories
GET /api/v1/memories
GET /api/v1/memories/{memory_id}
PUT /api/v1/memories/{memory_id}
DELETE /api/v1/memories/{memory_id}

POST /api/v1/memories/search
POST /api/v1/memories/classify
GET /api/v1/memories/write-decisions
POST /api/v1/memories/write-decisions/{decision_id}/approve
POST /api/v1/memories/write-decisions/{decision_id}/reject
```

用途：

```text
让用户能查看、搜索、编辑、删除记忆，也能处理需要确认的记忆写入候选。
```

---

### 8.2 Conversation Summary API

```text
POST /api/v1/conversations/{conversation_id}/summaries
GET /api/v1/conversations/{conversation_id}/summaries
GET /api/v1/conversations/{conversation_id}/summaries/latest
```

用途：

```text
让长对话能够被压缩进 Context Engine。
```

---

### 8.3 Agent Runtime API

```text
POST /api/v1/agent-runs
GET /api/v1/agent-runs
GET /api/v1/agent-runs/{agent_run_id}
GET /api/v1/agent-runs/{agent_run_id}/steps
GET /api/v1/agent-runs/{agent_run_id}/events
GET /api/v1/agent-runs/{agent_run_id}/plan
POST /api/v1/agent-runs/{agent_run_id}/cancel
POST /api/v1/agent-runs/{agent_run_id}/pause
POST /api/v1/agent-runs/{agent_run_id}/resume
POST /api/v1/agent-runs/{agent_run_id}/retry
```

用途：

```text
让前端可以启动、查看、暂停、恢复和重试 Agent Run。
```

---

### 8.4 Approval API

```text
GET /api/v1/agent-approvals
GET /api/v1/agent-approvals/{approval_id}
POST /api/v1/agent-approvals/{approval_id}/approve
POST /api/v1/agent-approvals/{approval_id}/reject
```

用途：

```text
让高风险 Tool Call 在执行前经过用户确认。
```

---

### 8.5 Context Preview API

```text
POST /api/v1/context/preview
```

用途：

```text
调试一次 Agent 运行前，模型到底会看到哪些上下文来源。
```

---

### 8.6 Agent Evaluation API

```text
POST /api/v1/agent-evaluations/datasets
GET /api/v1/agent-evaluations/datasets
POST /api/v1/agent-evaluations/datasets/{dataset_id}/cases
POST /api/v1/agent-evaluations/runs
GET /api/v1/agent-evaluations/runs
GET /api/v1/agent-evaluations/runs/{run_id}/results
```

用途：

```text
复用 Plan 4 的 Evaluation 思路，评测 Agent 是否正确规划、正确调用工具、正确遵守权限边界。
```

---

## 9. Plan 5 核心数据结构

### 9.1 Memory

```python
class Memory:
    id: str
    scope_type: str
    scope_id: str | None
    memory_type: str
    title: str
    content: str
    structured: dict
    importance: float
    confidence: float
    sensitivity: str
    status: str
```

---

### 9.2 MemoryCandidate

```python
class MemoryCandidate:
    content: str
    proposed_memory_type: str
    importance: float
    confidence: float
    sensitivity: str
    reason: str
```

---

### 9.3 MemorySearchResult

```python
class MemorySearchResult:
    memory_id: str
    content: str
    score: float
    rank: int
    reason: str
```

---

### 9.4 ContextBuildRequest

```python
class ContextBuildRequest:
    user_input: str
    conversation_id: str | None
    project_id: str | None
    agent_run_id: str | None
    include_memory: bool
    include_rag: bool
    token_budget: int
```

---

### 9.5 ContextBundle

```python
class ContextBundle:
    messages: list[dict]
    sections: list["ContextSection"]
    token_estimate: int
    selected_memory_ids: list[str]
    selected_source_ids: list[str]
```

---

### 9.6 AgentRun

```python
class AgentRun:
    id: str
    run_mode: str
    goal: str
    status: str
    current_step_index: int
    max_steps: int
    trace_run_id: str
```

---

### 9.7 AgentStep

```python
class AgentStep:
    id: str
    agent_run_id: str
    step_index: int
    step_type: str
    thought: str | None
    action_name: str | None
    action_input: dict | None
    observation: str | None
    status: str
```

---

### 9.8 AgentPlan

```python
class AgentPlan:
    id: str
    agent_run_id: str
    goal: str
    items: list["AgentPlanItem"]
    status: str
```

---

### 9.9 ApprovalRequest

```python
class ApprovalRequest:
    id: str
    agent_run_id: str
    agent_step_id: str
    risk_level: str
    action_name: str
    action_input: dict
    reason: str
    status: str
```

---

### 9.10 RuntimePolicy

```python
class RuntimePolicy:
    max_steps: int
    max_retries_per_step: int
    require_approval_for_risk_level: str
    allow_memory_write: bool
    allow_tool_write: bool
    allow_shell: bool
```

---

## 10. Plan 5 详细步骤

## Step 1：确认 Plan 4 封版状态

### 要做什么

检查 v0.4.0 是否稳定。

### 检查清单

```text
[ ] 基础 Chat 可用
[ ] Tool Calling 可用
[ ] Simple Agent Loop 可用
[ ] Knowledge Base 可用
[ ] Naive RAG 可用
[ ] Advanced RAG 可用
[ ] Hybrid Search 可用
[ ] Rerank 可用
[ ] RAG Evaluation 可用
[ ] Trace Run / Step 可用
[ ] Trace Timeline 可用
[ ] Token / Cost / Latency 可见
[ ] 已创建 tag v0.4.0
```

### 完成标准

```text
Plan 5 不重写 Trace、RAG、Tool Registry，只在它们之上构建 Runtime。
```

### 预计时间

2～4 小时

---

## Step 2：设计 Memory 数据模型

### 要做什么

创建 Memory 相关数据库模型。

### 任务清单

```text
[ ] 创建 models/memory.py
[ ] 定义 Memory ORM
[ ] 定义 MemoryWriteDecision ORM
[ ] 定义 MemoryRetrievalRun ORM
[ ] 定义 MemoryRetrievalCandidate ORM
[ ] 定义 ConversationSummary ORM
[ ] 创建 schemas/memory.py
[ ] 创建 Alembic migration
[ ] 写基础数据库测试
```

### 为什么做

Memory 不是 RAG 文档库。

Memory 面向用户、项目、会话和任务历史，需要能被查看、编辑、删除、审计。

### 完成标准

```text
可以创建、查询、更新、删除一条 memory，并能记录一次 memory 写入决策。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(memory): add memory data models
```

---

## Step 3：实现 Memory Service

### 要做什么

封装 Memory 的 CRUD 和状态管理。

### 任务清单

```text
[ ] 创建 memory/memory_service.py
[ ] 实现 create_memory()
[ ] 实现 update_memory()
[ ] 实现 archive_memory()
[ ] 实现 delete_memory()
[ ] 实现 list_memories()
[ ] 实现 get_memory()
[ ] 支持按 scope_type / memory_type / status 过滤
```

### 完成标准

```text
业务代码不直接操作 Memory ORM，而是通过 MemoryService 管理记忆。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(memory): add memory service
```

---

## Step 4：实现 Memory API

### 要做什么

对外暴露记忆管理接口。

### 任务清单

```text
[ ] 创建 api/v1/memories.py
[ ] POST /api/v1/memories
[ ] GET /api/v1/memories
[ ] GET /api/v1/memories/{memory_id}
[ ] PUT /api/v1/memories/{memory_id}
[ ] DELETE /api/v1/memories/{memory_id}
[ ] 支持分页和过滤
```

### 完成标准

```text
Swagger 可以创建、查看、编辑、删除 Memory。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(memory): add memory api
```

---

## Step 5：实现 Conversation Summary Memory

### 要做什么

给长对话增加滚动摘要能力。

### 任务清单

```text
[ ] 创建 memory/conversation_summary.py
[ ] 统计会话消息 token
[ ] 超过阈值时生成摘要
[ ] 保存 conversation_summaries
[ ] 摘要失败时保留原消息
[ ] 支持读取 latest summary
```

### Prompt 建议

```text
请总结这段对话中对后续有用的信息。
保留用户目标、项目背景、重要决策、未完成任务和偏好。
不要保留闲聊、重复内容和短期情绪。
输出简洁中文。
```

### 完成标准

```text
长会话可以生成 summary，并被后续 Context Engine 使用。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(memory): add conversation summary memory
```

---

## Step 6：实现 Profile / Project Memory

### 要做什么

支持用户偏好和项目背景记忆。

### 任务清单

```text
[ ] 定义 profile memory 写入格式
[ ] 定义 project memory 写入格式
[ ] 支持手动创建 profile memory
[ ] 支持手动创建 project memory
[ ] 支持 structured_json 编辑
[ ] 前端展示 memory scope 和 memory type
```

### 示例

```json
{
  "memory_type": "profile",
  "title": "用户偏好：中文直接表达",
  "content": "用户偏好使用中文，喜欢直接、结构清晰的技术解释。",
  "structured": {
    "language": "zh-CN",
    "style": "direct_structured"
  }
}
```

### 完成标准

```text
用户可以手动维护自己的偏好和项目背景。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(memory): support profile and project memories
```

---

## Step 7：实现 Memory Classifier

### 要做什么

判断一段对话是否值得写入长期记忆。

### 任务清单

```text
[ ] 创建 memory/memory_classifier.py
[ ] 输入 user_message / assistant_message / current_context
[ ] 输出 MemoryCandidate
[ ] 判断 memory_type
[ ] 判断 importance
[ ] 判断 confidence
[ ] 判断 sensitivity
[ ] 记录 memory_write_decisions
```

### 分类标准

```text
应该写入：
- 用户长期偏好
- 项目长期事实
- 稳定技术决策
- 未完成任务
- 用户明确要求记住的信息

不应写入：
- 一次性问题
- 临时情绪
- 重复信息
- 高敏感隐私
- 不确定的推测
```

### 完成标准

```text
一次对话结束后，系统可以生成 memory write decision，并说明为什么写或不写。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(memory): add memory classifier
```

---

## Step 8：实现 Memory 去重与敏感信息检查

### 要做什么

避免重复记忆和不合适的记忆写入。

### 任务清单

```text
[ ] 创建 memory/memory_deduper.py
[ ] 基于文本相似度检查重复
[ ] 基于 memory_type 和 scope 缩小候选
[ ] 创建 memory/memory_sensitivity.py
[ ] 识别 API Key / 密码 / 证件号等高敏感内容
[ ] 高敏感内容默认不自动写入
[ ] 需要确认的内容生成 approval-like decision
```

### 完成标准

```text
重复内容不会生成多条 Memory；敏感内容不会静默进入长期记忆。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(memory): add dedupe and sensitivity checks
```

---

## Step 9：实现 Memory 检索

### 要做什么

让 Agent 能按当前任务检索相关记忆。

### 任务清单

```text
[ ] 创建 memory/memory_retriever.py
[ ] 支持关键词过滤
[ ] 支持 memory_type 过滤
[ ] 支持 scope_type 过滤
[ ] 支持向量检索或轻量相似度检索
[ ] 记录 memory_retrieval_runs
[ ] 记录 memory_retrieval_candidates
```

### 初版建议

```text
如果 Plan 3/4 已有 Embedding 和 Vector Store，可复用 Qdrant 存 Memory 向量。
如果时间紧，可以先用 SQLite LIKE + 简单关键词评分，再保留向量扩展接口。
```

### 完成标准

```text
输入当前问题后，可以返回相关 Memory，并记录检索过程。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(memory): add memory retrieval
```

---

## Step 10：实现 Memory Injection

### 要做什么

把相关 Memory 注入到模型上下文中。

### 任务清单

```text
[ ] 创建 memory/memory_injector.py
[ ] 定义 Memory prompt section
[ ] 限制注入 token 上限
[ ] 按 importance / relevance 排序
[ ] 区分 profile / project / episodic / semantic memory
[ ] 记录哪些 memory 被注入
```

### Prompt Section 建议

```text
[User Memory]
- 用户偏好：...
- 项目背景：...
- 相关历史事实：...

这些记忆用于帮助你理解上下文。
如果当前问题与记忆无关，不要强行引用。
```

### 完成标准

```text
Agent 回答时可以使用相关 Memory，并在 Trace 中看到注入了哪些记忆。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(memory): inject relevant memories into context
```

---

## Step 11：实现 Memory 管理页面

### 要做什么

让用户能查看、编辑、删除和搜索记忆。

### 页面功能

```text
[ ] Memory 列表
[ ] 按 type / scope / status 过滤
[ ] Memory 详情编辑
[ ] Memory 搜索
[ ] Memory 写入候选列表
[ ] Approve / Reject 写入候选
[ ] 显示来源和最后使用时间
```

### 组件建议

```text
MemoryPage
MemoryList
MemoryEditor
MemoryCandidatePanel
MemorySourceBadge
MemorySearchPanel
```

### 完成标准

```text
用户对长期记忆有可见和可控的管理入口。
```

### 预计时间

12～18 小时

### 建议 commit

```text
feat(frontend): add memory management page
```

---

## Step 12：设计 Context Engine

### 要做什么

统一管理模型每次应该看到的上下文。

### 任务清单

```text
[ ] 创建 context_engine/context_types.py
[ ] 定义 ContextSection
[ ] 定义 ContextBundle
[ ] 定义 ContextBuildRequest
[ ] 定义上下文来源优先级
[ ] 定义 token budget 分配策略
```

### 推荐上下文结构

```text
[System Prompt]
[Agent Role]
[Tool Definitions]
[Runtime Policy]
[Project Memory]
[User Profile Memory]
[Relevant Long-term Memory]
[RAG Context]
[Conversation Summary]
[Recent Messages]
[Current Task State]
[Current User Input]
```

### 完成标准

```text
上下文构造不再散落在 Chat、RAG、Agent 各处，而是由 Context Engine 统一编排。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(context): add context engine types
```

---

## Step 13：实现 Token Budget 和 Source Selector

### 要做什么

避免模型上下文无限膨胀。

### 任务清单

```text
[ ] 创建 context_engine/token_budget.py
[ ] 创建 context_engine/source_selector.py
[ ] 估算每个 context section token
[ ] 固定保留 system / tool definitions
[ ] 给 memory / rag / history 分配预算
[ ] 超预算时按优先级裁剪
[ ] 输出 ContextBundle token_estimate
```

### 初版预算建议

```text
System + Tool Definitions：20%
Memory：15%
RAG Context：30%
Conversation Summary：10%
Recent Messages：15%
Current Input + Runtime State：10%
```

### 完成标准

```text
同一个请求可以看到 Context Preview，知道哪些内容被选中、哪些被裁剪。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(context): add token budget and source selection
```

---

## Step 14：实现 Context Builder

### 要做什么

串联 Memory、RAG、History、Tool、Runtime State，生成最终 messages。

### 任务清单

```text
[ ] 创建 context_engine/context_builder.py
[ ] 接入 conversation summary
[ ] 接入 recent messages
[ ] 接入 memory retriever
[ ] 接入 RAG retriever
[ ] 接入 tool definitions
[ ] 接入 runtime policy
[ ] 输出 messages
[ ] 记录 build_context trace_step
```

### 完成标准

```text
Agent Runtime 调用模型前，统一通过 ContextBuilder 构造 messages。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(context): build agent context bundles
```

---

## Step 15：设计 Agent Runtime v2 数据模型

### 要做什么

把 Simple Agent Loop 升级为明确的 Run / Step / Event / Checkpoint。

### 任务清单

```text
[ ] 创建 models/agent_runtime.py
[ ] 扩展或创建 AgentRun ORM
[ ] 扩展或创建 AgentStep ORM
[ ] 创建 AgentPlan ORM
[ ] 创建 AgentPlanItem ORM
[ ] 创建 AgentCheckpoint ORM
[ ] 创建 schemas/agent_runtime.py
[ ] 创建 Alembic migration
[ ] 写数据库测试
```

### 完成标准

```text
一次 Agent 运行可以保存状态、步骤、计划和检查点。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(agent): add runtime data models
```

---

## Step 16：实现 Runtime State Machine

### 要做什么

为 Agent Run 定义清晰状态流转。

### 任务清单

```text
[ ] 创建 agents/runtime/runtime_state.py
[ ] 定义 AgentRunStatus
[ ] 定义 AgentStepStatus
[ ] 定义允许的状态转移
[ ] 实现 transition_run_status()
[ ] 实现 transition_step_status()
[ ] 非法状态转移抛出 RuntimeStateError
```

### 状态流转建议

```text
queued -> running
running -> waiting_approval
waiting_approval -> running
running -> retrying
retrying -> running
running -> paused
paused -> running
running -> completed
running -> failed
running -> cancelled
```

### 完成标准

```text
Agent Run 不再只是 while loop，而是可解释的状态机。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(agent): add runtime state machine
```

---

## Step 17：实现 Runtime Policy

### 要做什么

定义 Agent 执行边界。

### 任务清单

```text
[ ] 创建 agents/runtime/runtime_policy.py
[ ] 支持 max_steps
[ ] 支持 max_retries_per_step
[ ] 支持 allowed_tools
[ ] 支持 denied_tools
[ ] 支持 require_approval_for_risk_level
[ ] 支持 allow_memory_write
[ ] 支持 allow_tool_write
[ ] 支持 allow_shell
```

### 默认策略建议

```json
{
  "max_steps": 12,
  "max_retries_per_step": 2,
  "require_approval_for_risk_level": "medium",
  "allow_memory_write": true,
  "allow_tool_write": false,
  "allow_shell": false
}
```

### 完成标准

```text
不同 Agent Run 可以带不同执行策略，Runtime 根据策略限制工具和动作。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(agent): add runtime policy
```

---

## Step 18：实现 Agent Runtime Service

### 要做什么

创建核心 Runtime 执行入口。

### 任务清单

```text
[ ] 创建 agents/runtime/agent_runtime.py
[ ] 实现 create_run()
[ ] 实现 run()
[ ] 实现 run_step()
[ ] 实现 finish_run()
[ ] 实现 fail_run()
[ ] 接入 trace_service
[ ] 接入 context_builder
[ ] 接入 tool_registry
[ ] 接入 runtime_policy
```

### 完成标准

```text
可以用 AgentRuntime 启动一次 agent_run，并保存 run / step / trace。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(agent): implement runtime service
```

---

## Step 19：实现 ReAct Agent

### 要做什么

实现 Thought / Action / Observation 循环。

### 任务清单

```text
[ ] 创建 agents/patterns/react_agent.py
[ ] 定义 ReAct prompt
[ ] 支持 Thought 输出
[ ] 支持 Action JSON 输出
[ ] 调用 Tool Registry 执行动作
[ ] 保存 Observation
[ ] 达到 Final Answer 后结束
[ ] 超过 max_steps 后失败并给出原因
```

### 输出格式建议

```json
{
  "thought": "我需要先查看项目文档。",
  "action": {
    "name": "read_file",
    "arguments": {
      "path": "README.md"
    }
  }
}
```

### 完成标准

```text
用户给一个需要工具的任务时，Agent 可以按 ReAct 循环执行，并在前端看到 Thought / Action / Observation。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(agent): add react agent pattern
```

---

## Step 20：接入 Tool Risk Policy

### 要做什么

在工具执行前判断风险等级。

### 任务清单

```text
[ ] 创建 agents/approval/risk_policy.py
[ ] 给工具定义 risk_level
[ ] 读取类工具默认为 low
[ ] 写入类工具默认为 medium
[ ] 执行命令类工具默认为 high
[ ] 网络访问类工具按配置判断
[ ] Runtime 根据 risk_level 决定是否需要 approval
```

### 风险等级建议

```text
low：只读、无外部副作用
medium：写文件、修改本地状态、调用付费 API
high：删除、覆盖、执行命令、访问外网、提交 Git、修改数据库
```

### 完成标准

```text
高风险工具不会被 Agent 静默执行。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(agent): add tool risk policy
```

---

## Step 21：实现 Human Approval

### 要做什么

让高风险步骤在执行前暂停并等待用户确认。

### 任务清单

```text
[ ] 创建 models/approval.py
[ ] 创建 agents/approval/approval_service.py
[ ] 创建 approval_requests 表
[ ] 工具执行前创建 approval_request
[ ] agent_run 状态改为 waiting_approval
[ ] 用户 approve 后继续执行
[ ] 用户 reject 后跳过或结束
[ ] 记录 approval trace_step
```

### 完成标准

```text
Agent 想执行高风险工具时，前端出现审批卡片；用户批准后才继续。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(agent): add human approval flow
```

---

## Step 22：实现 Approval API 和前端卡片

### 要做什么

让用户能处理审批请求。

### 任务清单

```text
[ ] GET /api/v1/agent-approvals
[ ] GET /api/v1/agent-approvals/{approval_id}
[ ] POST /api/v1/agent-approvals/{approval_id}/approve
[ ] POST /api/v1/agent-approvals/{approval_id}/reject
[ ] 前端 ApprovalRequestCard
[ ] AgentRunDetailPage 中展示 pending approval
```

### 完成标准

```text
用户可以在前端批准或拒绝一次 Agent 动作。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(frontend): add agent approval controls
```

---

## Step 23：实现 Retry 与 Error Recovery

### 要做什么

让 Runtime 遇到可恢复错误时有明确策略。

### 任务清单

```text
[ ] 创建 agents/runtime/recovery.py
[ ] 定义 error_type
[ ] Provider 超时可重试
[ ] JSON 解析失败可让模型修正
[ ] 工具参数校验失败可重试
[ ] 工具权限失败不可重试
[ ] 达到 max_retries 后 fail step
[ ] Trace 中记录 retry_count 和 error_message
```

### 错误类型建议

```text
llm_timeout
llm_rate_limit
tool_validation_error
tool_execution_error
permission_denied
approval_rejected
json_parse_error
context_overflow
```

### 完成标准

```text
常见错误不会直接让整个 Agent 崩掉；不可恢复错误有清晰原因。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(agent): add retry and error recovery
```

---

## Step 24：实现 Checkpoint / Pause / Resume

### 要做什么

保存 Agent 运行状态，使其可以暂停和恢复。

### 任务清单

```text
[ ] 创建 agents/runtime/checkpoint_service.py
[ ] 每个 step 完成后保存 checkpoint
[ ] 保存 context_snapshot
[ ] 保存 current_step_index
[ ] 实现 pause_run()
[ ] 实现 resume_run()
[ ] 实现 cancel_run()
[ ] 恢复后从最近 checkpoint 继续
```

### 初版说明

```text
Plan 5 初版可以只支持“步骤边界恢复”。
不要求在一个正在执行的 LLM streaming 中间恢复。
```

### 完成标准

```text
Agent Run 可以暂停、恢复、取消，刷新页面后仍能查看当前状态。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(agent): add checkpoints and resume
```

---

## Step 25：实现 Planner-Executor

### 要做什么

让 Agent 能先规划，再执行。

### 任务清单

```text
[ ] 创建 agents/patterns/planner_executor.py
[ ] 定义 planner prompt
[ ] 生成 AgentPlan
[ ] 保存 AgentPlanItem
[ ] Executor 按 plan item 执行
[ ] 每个 item 关联 agent_step
[ ] 计划变化时记录 revision
```

### Planner Prompt 建议

```text
请把用户任务拆成 3 到 8 个可执行步骤。
每一步要有明确目标。
不要包含需要用户自己完成的步骤。
如果步骤涉及高风险动作，标记 risk_level。
输出 JSON。
```

### 完成标准

```text
复杂任务会先生成计划，前端可以看到计划树和每一步执行状态。
```

### 预计时间

12～18 小时

### 建议 commit

```text
feat(agent): add planner executor pattern
```

---

## Step 26：实现 Reflection

### 要做什么

让 Agent 在输出前做轻量自检。

### 任务清单

```text
[ ] 创建 agents/patterns/reflection.py
[ ] 定义 reflection prompt
[ ] 检查是否完成用户目标
[ ] 检查是否引用了不存在的结果
[ ] 检查是否违反 runtime_policy
[ ] 需要修正时生成 revised_answer
[ ] 记录 reflection trace_step
```

### 输出示例

```json
{
  "passed": true,
  "issues": [],
  "revised_answer": null
}
```

### 完成标准

```text
Agent 最终回答前可以留下自检记录；自检失败时能修正答案或标记风险。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(agent): add reflection step
```

---

## Step 27：实现 Agent Runtime API

### 要做什么

把 Runtime 能力暴露给前端。

### 任务清单

```text
[ ] 创建 api/v1/agent_runs.py
[ ] POST /api/v1/agent-runs
[ ] GET /api/v1/agent-runs
[ ] GET /api/v1/agent-runs/{agent_run_id}
[ ] GET /api/v1/agent-runs/{agent_run_id}/steps
[ ] GET /api/v1/agent-runs/{agent_run_id}/events
[ ] GET /api/v1/agent-runs/{agent_run_id}/plan
[ ] POST /api/v1/agent-runs/{agent_run_id}/pause
[ ] POST /api/v1/agent-runs/{agent_run_id}/resume
[ ] POST /api/v1/agent-runs/{agent_run_id}/cancel
[ ] POST /api/v1/agent-runs/{agent_run_id}/retry
```

### 完成标准

```text
Swagger 可以启动 ReAct 或 Planner-Executor Agent，并查看步骤和状态。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(agent): add agent runtime api
```

---

## Step 28：实现 Agent Runtime 前端页面

### 要做什么

让用户可以启动和观察多步 Agent。

### 页面功能

```text
[ ] Agent Run 创建表单
[ ] Run Mode 选择
[ ] Runtime Policy 配置
[ ] Agent Run 列表
[ ] Agent Run 详情
[ ] Plan Tree
[ ] Step Timeline
[ ] Thought / Action / Observation 展示
[ ] Approval 卡片
[ ] Pause / Resume / Cancel / Retry 按钮
[ ] 跳转 Trace Timeline
```

### 组件建议

```text
AgentRuntimePage
AgentRunDetailPage
AgentRunPanel
AgentPlanTree
AgentStepTimeline
ThoughtActionObservation
ApprovalRequestCard
RuntimeStateBadge
RecoveryPanel
```

### 完成标准

```text
用户可以在页面上启动一个多步任务，并看到 Agent 如何计划、执行、等待审批、恢复和完成。
```

### 预计时间

18～28 小时

### 建议 commit

```text
feat(frontend): add agent runtime workspace
```

---

## Step 29：接入 Trace Timeline

### 要做什么

把 Plan 5 的 Runtime Step 统一写入 Plan 4 的 Trace。

### 任务清单

```text
[ ] agent_run 创建 trace_run
[ ] build_context 写 trace_step
[ ] memory_retrieve 写 trace_step
[ ] plan 写 trace_step
[ ] thought/action/observation 写 trace_step
[ ] approval 写 trace_step
[ ] retry/error 写 trace_step
[ ] reflection 写 trace_step
[ ] final_answer 写 trace_step
[ ] 前端 AgentRunDetailPage 可跳转 TracePage
```

### 完成标准

```text
一次 Agent Run 可以在 Trace Timeline 中完整复盘。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(agent): trace agent runtime steps
```

---

## Step 30：实现 Memory 自动写入闭环

### 要做什么

让 Agent Run 结束后，自动判断是否写入 Memory。

### 任务清单

```text
[ ] Agent Run 完成后调用 Memory Classifier
[ ] 生成 MemoryCandidate
[ ] 执行 dedupe 和 sensitivity check
[ ] 低风险高置信度自动写入
[ ] 需要用户确认的写入 decision
[ ] 前端 MemoryCandidatePanel 展示候选
[ ] 写入结果关联 trace_run / agent_run
```

### 完成标准

```text
稳定的用户偏好和项目事实可以进入长期记忆；用户能审核候选记忆。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(memory): close memory write loop
```

---

## Step 31：实现 Context Preview 页面

### 要做什么

帮助调试 Agent 上下文工程。

### 页面功能

```text
[ ] 输入当前用户问题
[ ] 选择 conversation / project / knowledge base
[ ] 预览 system prompt
[ ] 预览 memory section
[ ] 预览 rag section
[ ] 预览 conversation summary
[ ] 预览 token budget
[ ] 显示被裁剪的来源
```

### 完成标准

```text
用户能看到模型真正收到的上下文组成。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(frontend): add context preview
```

---

## Step 32：实现 Agent Evaluation 初版

### 要做什么

对 Agent 任务执行质量做基础评测。

### 指标范围

```text
[ ] Task Success
[ ] Expected Tool Hit
[ ] Forbidden Action Avoided
[ ] Step Count
[ ] Error Recovery Success
[ ] Approval Compliance
[ ] Final Answer Keyword Hit
[ ] Cost / Latency
```

### 任务清单

```text
[ ] 创建 agents/evaluation/agent_eval_types.py
[ ] 创建 agents/evaluation/agent_eval_runner.py
[ ] 创建 agents/evaluation/agent_metrics.py
[ ] 复用 Plan 4 eval_datasets / eval_runs 思路
[ ] 支持 mock tool 评测
[ ] 记录 eval trace
```

### 完成标准

```text
可以用小型测试集评测 ReAct / Planner-Executor 在固定任务上的表现。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(evaluation): add agent runtime evaluation
```

---

## Step 33：补充 Plan 5 测试

### 要做什么

给 Memory、Context Engine、Agent Runtime 写基础测试。

### 测试范围

```text
[ ] Memory CRUD 测试
[ ] Memory Classifier mock 测试
[ ] Memory dedupe 测试
[ ] Memory sensitivity 测试
[ ] Memory retrieval 测试
[ ] Memory injection 测试
[ ] Conversation summary mock 测试
[ ] Token budget 测试
[ ] Context builder 测试
[ ] Runtime state transition 测试
[ ] Runtime policy 测试
[ ] ReAct parser 测试
[ ] Tool risk policy 测试
[ ] Human approval 测试
[ ] Retry recovery 测试
[ ] Checkpoint resume 测试
[ ] Planner output parser 测试
[ ] Reflection mock 测试
[ ] Agent Runtime API 测试
```

### 完成标准

```text
核心 Runtime 行为不依赖真实模型也能用 mock 跑通主要逻辑。
```

### 预计时间

14～22 小时

### 建议 commit

```text
test(agent): add memory and runtime tests
```

---

## Step 34：补充 Plan 5 文档

### 要做什么

写清楚 Memory 和 Agent Runtime 的设计。

### 文档建议

```text
docs/22-plan-5-agent-runtime.md
docs/23-memory-architecture.md
docs/24-context-engine.md
docs/25-agent-runtime-state-machine.md
docs/26-react-agent.md
docs/27-planner-executor.md
docs/28-human-approval-and-recovery.md
docs/29-agent-evaluation.md
```

### 每篇文档写什么

```text
1. 模块目标
2. 为什么这样设计
3. 核心数据结构
4. API 说明
5. 当前限制
6. 与 Trace / RAG / Tool Registry 的关系
7. 如何调试一次 Agent Run
```

### 完成标准

```text
别人看文档能理解：
Memory 不等于 RAG；
Context Engine 如何选择上下文；
Agent Runtime 如何从 Simple Loop 升级为状态机；
Human Approval 如何控制风险；
Checkpoint / Resume 如何让长任务可恢复。
```

### 预计时间

8～12 小时

### 建议 commit

```text
docs: add plan 5 agent runtime documents
```

---

## Step 35：Plan 5 封版

### 要做什么

发布 v0.5.0。

### 任务清单

```text
[ ] 更新 README
[ ] 更新 CHANGELOG.md
[ ] 截图 Memory 页面
[ ] 截图 Agent Runtime 页面
[ ] 截图 Agent Run Detail 页面
[ ] 截图 Human Approval 卡片
[ ] 截图 Context Preview 页面
[ ] 记录当前支持的 Agent Run Mode
[ ] 记录当前支持的 Memory 类型
[ ] 记录当前 Runtime Policy 限制
[ ] 记录当前 Agent Evaluation 指标
[ ] 创建 Git tag：v0.5.0
```

### 完成标准

```text
从 README 启动项目后，可以完成：
1. 手动创建用户偏好 Memory
2. 手动创建项目 Memory
3. 进行一次长对话并生成 Conversation Summary
4. 启动 ReAct Agent Run
5. 查看 Thought / Action / Observation
6. 启动 Planner-Executor Agent Run
7. 查看 Plan Tree 和 Step Timeline
8. 对高风险工具调用进行 Human Approval
9. 暂停、恢复或取消 Agent Run
10. 查看 Agent Run 对应 Trace
11. 查看 Context Preview
12. 让系统生成 Memory 写入候选
13. 批准或拒绝 Memory 写入候选
14. 运行一组基础 Agent Evaluation
```

### 建议 commit

```text
chore: release v0.5.0 agent runtime
```

---

## 11. Plan 5 最终验收标准

Plan 5 完成后，必须满足：

```text
[ ] memories 表可用
[ ] memory_write_decisions 表可用
[ ] conversation_summaries 表可用
[ ] Memory CRUD 可用
[ ] Memory API 可用
[ ] Conversation Summary 可用
[ ] Profile Memory 可用
[ ] Project Memory 可用
[ ] Memory Classifier 可用
[ ] Memory 去重可用
[ ] Memory 敏感信息检查可用
[ ] Memory Retrieval 可用
[ ] Memory Injection 可用
[ ] Memory 管理页面可用
[ ] Context Engine 数据结构完成
[ ] Token Budget 可用
[ ] Context Builder 可用
[ ] Context Preview 可用
[ ] AgentRun / AgentStep 数据模型可用
[ ] Agent Runtime State Machine 可用
[ ] Runtime Policy 可用
[ ] ReAct Agent 可用
[ ] Tool Risk Policy 可用
[ ] Human Approval 可用
[ ] Approval API 可用
[ ] Approval 前端卡片可用
[ ] Retry / Error Recovery 可用
[ ] Checkpoint / Pause / Resume 可用
[ ] Planner-Executor 可用
[ ] Reflection 可用
[ ] Agent Runtime API 可用
[ ] Agent Runtime 前端页面可用
[ ] Agent Run 写入 Trace Timeline
[ ] Memory 自动写入闭环可用
[ ] Agent Evaluation 初版可用
[ ] 核心测试已补充
[ ] README 已更新
[ ] docs 已更新
[ ] 已创建 v0.5.0 tag
```

---

## 12. Plan 5 最小可交付版本

如果时间不够，Plan 5 最小版本只做：

```text
1. Memory 数据模型
2. Memory CRUD API
3. Memory 管理页面
4. Conversation Summary
5. Memory Classifier 初版
6. Memory Retrieval
7. Memory Injection
8. Context Builder
9. Token Budget
10. AgentRun / AgentStep 数据模型
11. Runtime State Machine
12. Runtime Policy
13. ReAct Agent
14. Tool Risk Policy
15. Human Approval
16. Agent Runtime API
17. Agent Run Detail 页面
18. Trace 接入
19. README 和文档更新
```

可以延期：

```text
1. Planner-Executor 的完整 UI
2. Reflection
3. Agent Evaluation
4. 复杂 Checkpoint / Resume
5. Context Preview 的完整可视化
6. Memory 向量检索优化
7. 自动 Memory 写入的高置信度策略
8. 异步 Worker 执行 Agent Run
```

不能延期：

```text
1. Memory 基础模型
2. Memory 可查看、可编辑、可删除
3. Memory 注入上下文
4. Context Engine
5. Agent Runtime 状态机
6. ReAct Agent
7. Human Approval
8. Trace 接入
```

如果按最小版本进入 Plan 6，必须先补齐以下桥接项：

```text
1. Tool Risk Policy 能对内置工具和外部工具使用同一套风险等级
2. Human Approval API 可被 MCP Tool Call 复用
3. Agent Runtime 可以接收动态注册工具，不需要为 MCP 重写执行循环
4. Agent Run Detail 页面能展示 Tool Call、Approval、Trace 三类事件
5. Checkpoint / Resume 至少支持 paused、running、completed、failed、cancelled 状态恢复
```

---

## 13. Plan 5 与 Plan 6 的衔接

Plan 5 完成后，项目具备：

```text
基础 Chat
多模型 Provider
Tool Calling
知识库系统
Naive RAG
Advanced RAG
Rerank
RAG Evaluation
Trace Timeline
Memory
Context Engine
ReAct Agent
Planner-Executor
Human Approval
Retry / Error Recovery
Checkpoint / Resume
Agent Evaluation
```

这为 Plan 6 的 Agent 工作台打基础。

Plan 6 不需要重新做：

```text
Memory
Context Engine
Agent Runtime 状态机
Human Approval
Tool Risk Policy
Trace Timeline
Agent Run 页面基础结构
```

Plan 6 可以在 Plan 5 的基础上扩展：

```text
MCP Client
Filesystem MCP
GitHub MCP
SQLite MCP
自定义 MCP Server
STT / TTS
Voice Agent
OCR / VLM
Electron / Tauri
本地文件访问
桌面快捷键
```

换句话说：

```text
Plan 5 让 Agent Runtime 真正成型。
Plan 6 让 Runtime 连接更大的工具生态和更完整的产品形态。
```

---

## 14. Plan 5 完成后的简历表达

可以写成：

```text
在 AI Agent Lab 中设计并实现核心 Agent Runtime，将早期 Simple Agent Loop 升级为支持 Memory、Context Engine、ReAct、Planner-Executor、Human Approval、Retry / Error Recovery、Checkpoint / Resume 和 Trace 可观测的工程化运行时。系统支持用户偏好、项目背景、会话摘要、事件记忆和语义记忆的管理与检索注入，能够对多步任务进行规划、执行、审批、恢复和复盘，并通过前端展示 Agent Run、Plan Tree、Thought / Action / Observation、审批请求、上下文预览和完整 Timeline。
```

亮点可以拆成：

```text
1. 设计 Memory 架构，区分 Profile、Project、Episodic、Semantic、Task Memory，并实现写入判断、去重、敏感信息检查和检索注入。
2. 构建 Context Engine，统一编排 System Prompt、Tool Definitions、Memory、RAG、Conversation Summary、Recent Messages 和 Runtime State。
3. 将 Simple Agent Loop 升级为 Agent Runtime 状态机，支持 Run / Step / Event / Checkpoint 的持久化和 Trace 复盘。
4. 实现 ReAct 和 Planner-Executor 两种 Agent 模式，使 Agent 能处理多步任务并展示计划执行过程。
5. 引入 Human Approval、Tool Risk Policy、Retry 和 Error Recovery，让 Agent 在高风险动作和失败场景下具备工程安全边界。
```

---

## 15. Plan 5 实施建议

Plan 5 是整个项目中最容易失控的一段。

推荐执行顺序：

```text
先做 Memory 可管理
再做 Context Engine
再做 Runtime 状态机
再做 ReAct
再做 Human Approval
最后做 Planner / Reflection / Evaluation
```

不要一开始就追求“超级智能 Agent”。

Plan 5 的关键不是让模型表现得多聪明，而是让系统具备：

```text
可控的上下文
可解释的状态
可审计的记忆
可暂停的运行
可确认的高风险动作
可复盘的执行轨迹
```

这些能力完成后，后面的 MCP、语音、多模态、桌面端才有稳定的运行时底座。
