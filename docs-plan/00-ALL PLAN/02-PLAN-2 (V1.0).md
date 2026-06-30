# Plan 2｜Agent 初版：Tool Calling + 简单 Agent Loop

## 0. 子计划定位

Plan 2 对应项目总路线中的：

```text
Phase 2：Tool Calling + 简单 Agent
```

Plan 2 的前置条件是：

```text
Plan 1 已完成
版本：v0.1.0
成果：基础 Chat 平台可运行
```

也就是说，项目已经具备：

- FastAPI 后端
    
- React WebUI
    
- SQLite 会话存储
    
- LLM Provider 抽象
    
- DeepSeek / OpenRouter / OpenAI-compatible Provider
    
- Chat API
    
- Streaming Chat
    
- 会话历史
    
- 模型选择
    
- Token / Cost / Latency 基础统计
    
- 基础日志和错误处理
    

Plan 2 不重写 Plan 1 的 Chat 系统，而是在 Plan 1 的基础上增加：

> Agent 调用工具的能力。

---

## 1. Plan 2 核心目标

Plan 2 的目标是：

> 让 AI Agent Lab 从“能聊天的 AI 应用”升级为“能调用工具完成简单任务的 Agent 初版”。

完成 Plan 2 后，系统应该支持：

```text
用户输入任务
    ↓
Agent 判断是否需要工具
    ↓
Agent 调用工具
    ↓
系统执行工具
    ↓
工具结果返回给 Agent
    ↓
Agent 整理最终答案
    ↓
前端展示工具调用过程和最终回答
```

最典型的验收场景：

```text
用户：读取 README.md，并总结这个项目的结构。

Agent：
1. 判断需要调用 read_file 工具
2. 调用 read_file("README.md")
3. 读取文件内容
4. 把文件内容返回给模型
5. 模型生成总结
6. 前端展示工具调用过程和最终回答
```

---

## 2. Plan 2 不做什么

为了避免项目失控，Plan 2 暂时不做以下内容：

|暂不做|原因|
|---|---|
|RAG|放到 Plan 3|
|文件上传知识库|放到 Plan 3|
|Embedding|放到 Plan 3|
|Qdrant|放到 Plan 3|
|Advanced RAG|放到 Plan 4|
|Memory|放到 Plan 5|
|复杂状态机|放到 Plan 5|
|Planner-Executor|放到 Plan 5|
|Reflection|放到 Plan 5|
|MCP|放到 Plan 6|
|Shell Tool|后续再做，风险较高|
|write_file / delete_file|后续再做，需要权限审批|
|Git commit / 数据库修改|后续再做，需要安全边界|

Plan 2 只做最小工具调用闭环。

---

## 3. Plan 2 版本目标

|项目|内容|
|---|---|
|子计划名称|Plan 2：Agent 初版|
|对应 Phase|Phase 2|
|起始版本|v0.1.0|
|目标版本|v0.2.0|
|核心能力|Tool Calling + 简单 Agent Loop|
|预计时间|60～100 小时|
|难度|中等偏高|
|项目价值|让系统第一次具备真正 Agent 能力|

---

## 4. Plan 2 技术重点

Plan 2 重点学习和实现：

- Tool 抽象
    
- Tool Registry
    
- JSON Schema
    
- 参数校验
    
- Tool Permission
    
- Tool Result
    
- Tool Call 记录
    
- 简单 Agent Loop
    
- LLM Tool Calling
    
- 前端 Tool Call 展示
    
- 工具安全边界
    
- 工具失败处理
    

---

## 5. Plan 2 最小工具集

Plan 2 只实现低风险只读工具。

### 5.1 read_file

用途：

```text
读取项目目录内的文本文件。
```

示例：

```json
{
  "path": "README.md"
}
```

限制：

- 只能读取项目 sandbox 目录内文件
    
- 禁止读取系统敏感路径
    
- 禁止读取 `.env`
    
- 禁止读取密钥文件
    
- 文件大小需要限制
    
- 超长内容需要截断或摘要
    

---

### 5.2 list_dir

用途：

```text
列出项目目录结构。
```

示例：

```json
{
  "path": ".",
  "max_depth": 2
}
```

限制：

- 只能列出项目 sandbox 目录
    
- 默认隐藏 `.git`
    
- 默认隐藏 `.env`
    
- 限制最大递归深度
    
- 限制最大返回条目数
    

---

### 5.3 web_fetch

用途：

```text
获取指定 URL 的网页文本内容。
```

示例：

```json
{
  "url": "https://example.com"
}
```

限制：

- 只做 fetch，不做浏览器自动化
    
- 限制超时时间
    
- 限制响应大小
    
- 禁止访问内网地址
    
- 失败要返回清晰错误
    

说明：

```text
web_fetch 可以先做成可选工具。
如果时间不够，Plan 2 最小版只做 read_file 和 list_dir。
```

---

## 6. Plan 2 推荐目录结构调整

在 Plan 1 目录基础上，新增以下模块：

```text
backend/app/
├── agents/
│   ├── simple_agent.py
│   ├── agent_types.py
│   └── agent_service.py
│
├── tools/
│   ├── base.py
│   ├── registry.py
│   ├── schemas.py
│   ├── builtin/
│   │   ├── read_file.py
│   │   ├── list_dir.py
│   │   └── web_fetch.py
│   └── security.py
│
├── models/
│   ├── tool_call.py
│   └── agent_run.py
│
├── schemas/
│   ├── tool.py
│   └── agent.py
│
└── api/v1/
    ├── agents.py
    └── tools.py
```

前端新增：

```text
frontend/src/
├── components/
│   └── agent/
│       ├── ToolCallCard.tsx
│       ├── ToolCallTimeline.tsx
│       └── AgentRunPanel.tsx
│
├── types/
│   ├── tool.ts
│   └── agent.ts
│
└── api/
    ├── agents.ts
    └── tools.ts
```

---

## 7. Plan 2 数据库设计

### 7.1 agent_runs

用于记录一次 Agent 执行。

```sql
agent_runs
- id
- conversation_id
- user_message_id
- status
- goal
- final_answer
- error_message
- started_at
- ended_at
- latency_ms
- created_at
```

状态建议：

```text
created
running
waiting_tool
completed
failed
cancelled
```

Plan 2 只需要简单状态，不需要完整状态机。

---

### 7.2 tool_calls

用于记录工具调用。

```sql
tool_calls
- id
- agent_run_id
- conversation_id
- tool_name
- arguments_json
- result_json
- status
- error_message
- started_at
- ended_at
- latency_ms
- created_at
```

状态建议：

```text
pending
running
success
failed
timeout
blocked
```

---

## 8. Plan 2 核心数据结构

### 8.1 Tool

```python
class Tool:
    name: str
    description: str
    parameters_schema: dict
    permission_level: str
    timeout_seconds: int

    async def run(self, arguments: dict) -> "ToolResult":
        ...
```

---

### 8.2 ToolResult

```python
class ToolResult:
    tool_name: str
    success: bool
    content: str
    data: dict | None
    error: str | None
    metadata: dict
```

---

### 8.3 ToolCall

```python
class ToolCall:
    id: str
    tool_name: str
    arguments: dict
    status: str
    result: ToolResult | None
```

---

### 8.4 AgentRun

```python
class AgentRun:
    id: str
    conversation_id: str
    goal: str
    status: str
    tool_calls: list[ToolCall]
    final_answer: str | None
```

---

## 9. Plan 2 详细步骤

## Step 1：确认 Plan 1 封版状态

### 要做什么

检查 v0.1.0 是否稳定。

### 检查清单

```text
[ ] 后端能启动
[ ] 前端能启动
[ ] Chat API 可用
[ ] Streaming 可用
[ ] 会话历史可用
[ ] LLM Provider 可用
[ ] 日志可用
[ ] README 可用
[ ] 已创建 tag v0.1.0
```

### 完成标准

```text
Plan 1 不再大改架构，只在其上扩展 Agent 模块。
```

### 预计时间

2～4 小时

---

## Step 2：设计 Tool 基础抽象

### 要做什么

创建工具基础接口。

### 任务清单

```text
[ ] 创建 backend/app/tools/base.py
[ ] 定义 Tool 类
[ ] 定义 ToolResult
[ ] 定义 ToolError
[ ] 定义 permission_level 字段
[ ] 定义 timeout_seconds 字段
[ ] 定义 parameters_schema 字段
```

### 为什么做

Agent 不能直接调用散乱函数，必须通过统一 Tool 抽象调用。

### 完成标准

```text
所有工具都可以通过统一接口 run(arguments) 执行。
```

### 预计时间

5～8 小时

### 建议 commit

```text
feat(tools): add base tool abstraction
```

---

## Step 3：实现 Tool Registry

### 要做什么

实现工具注册中心。

### 任务清单

```text
[ ] 创建 backend/app/tools/registry.py
[ ] 实现 register_tool()
[ ] 实现 get_tool()
[ ] 实现 list_tools()
[ ] 实现 get_openai_tool_schemas()
[ ] 启动时自动注册内置工具
```

### 为什么做

LLM 需要知道当前有哪些工具可以调用，Agent Runtime 也需要根据工具名找到对应实现。

### 完成标准

```text
后端能列出当前可用工具，并生成模型可识别的 tool schema。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(tools): add tool registry
```

---

## Step 4：实现工具参数校验

### 要做什么

基于 JSON Schema / Pydantic 校验工具参数。

### 任务清单

```text
[ ] 定义工具参数 schema
[ ] 工具执行前校验 arguments
[ ] 参数缺失时返回错误
[ ] 参数类型错误时返回错误
[ ] 错误写入 tool_calls
```

### 为什么做

模型生成的工具参数不一定可靠，必须校验。

### 完成标准

```text
错误参数不会导致后端崩溃。
```

### 预计时间

5～8 小时

### 建议 commit

```text
feat(tools): add tool argument validation
```

---

## Step 5：实现工具安全边界

### 要做什么

实现最低限度的安全控制。

### 任务清单

```text
[ ] 创建 backend/app/tools/security.py
[ ] 定义 PROJECT_WORKSPACE_ROOT
[ ] 限制文件工具只能访问 workspace
[ ] 禁止读取 .env
[ ] 禁止读取密钥文件
[ ] 禁止路径穿越 ../
[ ] 限制文件大小
[ ] 限制目录遍历深度
```

### 为什么做

只要 Agent 能调用工具，就必须有安全边界。

### 完成标准

```text
Agent 不能读取项目外文件，不能读取 .env。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(security): add basic tool permission guard
```

---

## Step 6：实现 read_file 工具

### 要做什么

实现读取文件工具。

### 任务清单

```text
[ ] 创建 tools/builtin/read_file.py
[ ] 定义参数 path
[ ] 校验路径
[ ] 读取文本文件
[ ] 限制最大字符数
[ ] 返回文件内容和 metadata
[ ] 写单元测试
```

### 完成标准

```text
read_file 可以读取 README.md，并返回内容。
```

### 预计时间

5～8 小时

### 建议 commit

```text
feat(tools): add read_file tool
```

---

## Step 7：实现 list_dir 工具

### 要做什么

实现目录列表工具。

### 任务清单

```text
[ ] 创建 tools/builtin/list_dir.py
[ ] 定义 path
[ ] 定义 max_depth
[ ] 校验路径
[ ] 遍历目录
[ ] 排除 .git / .env / __pycache__
[ ] 限制最大返回数量
[ ] 写单元测试
```

### 完成标准

```text
list_dir 可以展示项目目录结构。
```

### 预计时间

5～8 小时

### 建议 commit

```text
feat(tools): add list_dir tool
```

---

## Step 8：可选实现 web_fetch 工具

### 要做什么

实现简单网页内容获取工具。

### 任务清单

```text
[ ] 创建 tools/builtin/web_fetch.py
[ ] 定义 url 参数
[ ] 限制超时时间
[ ] 限制最大响应大小
[ ] 禁止访问 localhost / 内网地址
[ ] 提取网页文本
[ ] 返回标题和正文摘要
```

### 完成标准

```text
web_fetch 可以读取普通网页文本。
```

### 预计时间

8～12 小时

### 是否必须

```text
非必须。
如果 Plan 2 时间紧，可以延后到 Plan 4 或 Plan 6。
```

### 建议 commit

```text
feat(tools): add basic web_fetch tool
```

---

## Step 9：扩展 LLM Provider 支持 tools

### 要做什么

让 OpenAI-compatible Provider 支持 tools 参数。

### 任务清单

```text
[ ] ChatRequest 增加 tools 字段
[ ] ChatResponse 增加 tool_calls 字段
[ ] Provider 请求中传入 tools
[ ] 解析模型返回的 tool_calls
[ ] 兼容不支持 tools 的模型
[ ] 模型不支持 tools 时返回明确错误
```

### 为什么做

Tool Calling 要接入模型调用层，否则 Agent 无法让模型选择工具。

### 完成标准

```text
模型能返回 tool_calls，并被系统解析出来。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(llm): support tool calling in provider
```

---

## Step 10：实现 Simple Agent Loop

### 要做什么

实现最小 Agent Loop。

### 流程

```text
用户输入
    ↓
创建 agent_run
    ↓
构造 messages + tools
    ↓
调用 LLM
    ↓
如果模型返回 tool_call
    ↓
执行对应工具
    ↓
把 tool result 追加进 messages
    ↓
再次调用 LLM
    ↓
输出 final answer
```

### 任务清单

```text
[ ] 创建 agents/simple_agent.py
[ ] 创建 AgentRun 数据结构
[ ] 支持最多 N 次工具调用
[ ] 默认 max_steps = 3
[ ] 记录每次 tool_call
[ ] 处理工具失败
[ ] 生成 final_answer
```

### 为什么做

这是从 Chat 变成 Agent 的关键。

### 完成标准

```text
用户让 Agent 读取 README.md，Agent 能调用 read_file 后回答。
```

### 预计时间

12～20 小时

### 建议 commit

```text
feat(agent): add simple agent loop
```

---

## Step 11：实现 Agent API

### 要做什么

创建 Agent 执行接口。

### 接口建议

```text
POST /api/v1/agents/runs
GET /api/v1/agents/runs/{run_id}
GET /api/v1/agents/runs/{run_id}/tool-calls
```

### 请求示例

```json
{
  "conversation_id": "xxx",
  "provider": "deepseek",
  "model": "deepseek-chat",
  "input": "读取 README.md 并总结项目结构"
}
```

### 任务清单

```text
[ ] 创建 schemas/agent.py
[ ] 创建 api/v1/agents.py
[ ] 创建 agent_service.py
[ ] 接入 SimpleAgent
[ ] 保存 agent_run
[ ] 保存 tool_calls
[ ] 返回 final_answer
```

### 完成标准

```text
Swagger 可以调用 Agent API，并看到工具调用结果。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(agent): add agent run api
```

---

## Step 12：前端展示 Tool Call

### 要做什么

在 Chat UI 中展示 Agent 的工具调用过程。

### 组件建议

```text
ToolCallCard
ToolCallTimeline
AgentRunPanel
```

### 展示内容

```text
工具名称
参数
状态
耗时
结果摘要
错误信息
```

### 任务清单

```text
[ ] 创建 ToolCallCard
[ ] 创建 ToolCallTimeline
[ ] ChatPage 支持 Agent 模式
[ ] 用户输入后调用 Agent API
[ ] 展示工具调用过程
[ ] 展示最终回答
```

### 完成标准

```text
前端能看到：
1. Agent 调用了什么工具
2. 参数是什么
3. 工具是否成功
4. 最终回答是什么
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(frontend): show agent tool calls
```

---

## Step 13：补充 Tool / Agent 测试

### 要做什么

给工具和 Agent Loop 写基础测试。

### 测试范围

```text
[ ] read_file 正常读取
[ ] read_file 禁止读取 .env
[ ] read_file 禁止路径穿越
[ ] list_dir 正常列目录
[ ] list_dir 限制 max_depth
[ ] Tool Registry 正常注册工具
[ ] Simple Agent 能执行 read_file
[ ] 工具失败时 Agent 不崩溃
```

### 完成标准

```text
pytest 能跑通核心测试。
```

### 预计时间

8～12 小时

### 建议 commit

```text
test(agent): add basic tool and agent tests
```

---

## Step 14：补充 Plan 2 文档

### 要做什么

写清楚 Tool Calling 和 Simple Agent 设计。

### 文档建议

```text
docs/06-plan-2-basic-agent.md
docs/07-tool-calling.md
docs/08-simple-agent-loop.md
docs/09-tool-security.md
```

### 每篇文档写什么

```text
1. 模块目标
2. 为什么这样设计
3. 核心数据结构
4. API 说明
5. 安全限制
6. 当前不足
7. 后续扩展
```

### 完成标准

```text
别人看文档能理解 Plan 2 的 Agent 初版是怎么工作的。
```

### 预计时间

6～10 小时

### 建议 commit

```text
docs: add plan 2 basic agent documents
```

---

## Step 15：Plan 2 封版

### 要做什么

发布 v0.2.0。

### 任务清单

```text
[ ] 更新 README
[ ] 更新 CHANGELOG.md
[ ] 截图 Tool Call 展示界面
[ ] 记录当前支持的工具
[ ] 记录当前安全限制
[ ] 创建 Git tag：v0.2.0
```

### 完成标准

```text
从 README 启动项目后，可以完成：
读取 README.md 并总结项目结构。
```

### 建议 commit

```text
chore: release v0.2.0 basic agent
```

---

## 10. Plan 2 最终验收标准

Plan 2 完成后，必须满足：

```text
[ ] Tool 抽象完成
[ ] Tool Registry 完成
[ ] read_file 可用
[ ] list_dir 可用
[ ] 工具参数校验可用
[ ] 工具安全边界可用
[ ] LLM Provider 支持 tools
[ ] Simple Agent Loop 可用
[ ] Agent API 可用
[ ] 工具调用记录可保存
[ ] 前端能展示 Tool Call
[ ] 工具失败不会导致系统崩溃
[ ] README 已更新
[ ] docs 已更新
[ ] 已创建 v0.2.0 tag
```

---

## 11. Plan 2 最小可交付版本

如果时间不够，Plan 2 最小版只做：

```text
1. Tool 抽象
2. Tool Registry
3. read_file
4. list_dir
5. Provider 支持 tools
6. Simple Agent Loop
7. Agent API
8. 前端展示工具调用结果
```

可以延后：

```text
1. web_fetch
2. 完整 Tool Timeline
3. 复杂工具权限
4. 工具结果压缩
5. 更完整的测试覆盖
```

不能延后：

```text
1. read_file 安全限制
2. 路径限制
3. .env 禁止读取
4. Agent 最大步数限制
5. 工具调用日志
```

如果按最小版本进入 Plan 3，必须先补齐以下桥接项：

```text
1. Tool Registry 可以稳定注册后续 search_knowledge_base 工具
2. ToolResult 结构能表达 success、content、error、metadata
3. 工具调用日志能关联 conversation_id 或 agent_run_id
4. read_file / list_dir 的路径安全规则已经固定
5. Simple Agent Loop 有最大步数、超时和失败返回
```

---

## 12. Plan 2 与 Plan 3 的衔接

Plan 2 完成后，项目具备：

```text
Chat 能力
多模型能力
工具调用能力
简单 Agent Loop
文件读取能力
目录查看能力
工具调用记录
前端工具调用展示
```

这为 Plan 3 的知识库系统打基础。

Plan 3 不需要重新实现 Tool Calling，而是复用 Plan 2 的能力：

```text
Plan 2 的 read_file/list_dir
    ↓
Plan 3 的 document parser 可以读取上传文件
    ↓
Plan 3 的 RAG 检索可以作为新工具 search_knowledge_base
    ↓
Plan 5 的 Agent Runtime 可以把 RAG Tool 纳入多步 Agent
```

Plan 3 的目标不是推翻 Plan 2，而是在已有 Agent 工具体系旁边增加：

> Knowledge Base + Naive RAG。

---
