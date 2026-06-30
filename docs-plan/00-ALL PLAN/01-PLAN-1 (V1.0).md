# Plan 1｜项目基础平台：项目骨架 + 基础 Chat

## 0. 子计划定位

Plan 1 对应项目总路线中的：

```text
Phase 0：项目骨架
Phase 1：基础 Chat + 多模型 Provider
```

Plan 1 的目标是：

> 建立 AI Agent Lab 的工程地基，并实现一个支持多模型、流式输出、会话保存、Token / 成本统计的基础 AI Chat 工作台。

你的文档里 Phase 0 的目标是搭建基础工程结构，包括 Git、FastAPI、React、Docker Compose、数据库、环境变量、README 和架构文档；完成标准是前端能打开、后端能启动、能调用健康检查 API、Docker Compose 能启动基础服务。  
Phase 1 的目标是实现最小 AI 对话闭环，包括 LLM Provider 抽象、OpenAI-compatible API、DeepSeek、OpenRouter、Chat API、流式输出、前端 Chat UI、会话保存、Token 和成本统计。

---

## 1. Plan 1 总目标

|项目|内容|
|---|---|
|子计划名称|Plan 1：项目基础平台|
|对应阶段|Phase 0 + Phase 1|
|预计时间|75～120 小时|
|难度|中等|
|核心成果|一个自己的 Web ChatGPT 雏形|
|技术重点|FastAPI、React、LLM Provider、Streaming、SQLite、会话系统|
|最终版本号|v0.1.0|
|完成标志|可以在网页里选择模型、发送消息、流式返回、保存历史会话|

---

## 2. Plan 1 不做什么

这一阶段不要做：

| 暂不做          | 原因                |
| ------------ | ----------------- |
| RAG          | 放到 Plan 3         |
| Tool Calling | 放到 Plan 2         |
| Agent Loop   | 放到 Plan 2         |
| Memory       | 放到 Plan 5         |
| MCP          | 放到 Plan 6         |
| Electron     | 放到 Plan 6         |
| 语音           | 放到 Plan 6         |
| 多模态          | 放到 Plan 6         |
| 多 Agent      | 不急，甚至可以放到 v1.0 之后 |
| 完美 UI        | 第一阶段只要清晰可用        |

---

## 3. Plan 1 技术栈

第一版技术栈基本沿用你的文档：前端 React / Vite 或 Next.js、Tailwind、shadcn/ui；后端 Python、FastAPI、Pydantic、SQLAlchemy、SQLite、Qdrant、Redis；AI 侧使用 OpenAI-compatible Provider、DeepSeek、OpenRouter 等。

Plan 1 里建议实际使用：

|层|技术|
|---|---|
|前端|React + Vite + TypeScript|
|UI|Tailwind CSS + shadcn/ui|
|状态管理|Zustand|
|请求|fetch 封装即可，暂时不用复杂客户端|
|后端|FastAPI|
|配置|pydantic-settings|
|数据库|SQLite|
|ORM|SQLAlchemy|
|迁移|Alembic|
|流式输出|SSE|
|LLM 接入|OpenAI-compatible Provider|
|首选模型|DeepSeek 或 OpenRouter|
|日志|Python logging 或 loguru|
|包管理|uv|
|版本管理|Git|

暂时不用 PostgreSQL。SQLite 足够支撑 Plan 1。

---

## 4. Plan 1 目录结构

建议第一版目录不要太复杂，但要给后续模块预留位置。你的文档里已经设计了 backend/app/api、core、db、models、schemas、services、agents、providers、rag、memory、tools、mcp、workflows、evaluation、observability、security 等目录。

Plan 1 可以先这样落地：

```text

ai-agent-lab/
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── 00-project-overview.md
│   ├── 01-architecture.md
│   ├── 02-plan-1-foundation.md
│   └── 03-llm-provider.md
│
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── health.py
│   │   │       ├── chat.py
│   │   │       ├── conversations.py
│   │   │       └── models.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── errors.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   ├── models/
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   └── llm_call.py
│   │   ├── schemas/
│   │   │   ├── chat.py
│   │   │   ├── conversation.py
│   │   │   └── model.py
│   │   ├── services/
│   │   │   ├── chat_service.py
│   │   │   └── conversation_service.py
│   │   ├── providers/
│   │   │   └── llm/
│   │   │       ├── base.py
│   │   │       ├── openai_compatible.py
│   │   │       └── registry.py
│   │   └── prompts/
│   │       └── default_chat.md
│   └── tests/
│
└── frontend/
    ├── package.json
    ├── .env.example
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── api/
        │   ├── client.ts
        │   ├── chat.ts
        │   └── conversations.ts
        ├── pages/
        │   ├── ChatPage.tsx
        │   └── SettingsPage.tsx
        ├── components/
        │   ├── layout/
        │   └── chat/
        ├── stores/
        │   └── chatStore.ts
        └── types/
            └── chat.ts

```

---

## 5. Plan 1 详细步骤

## Step 1：创建仓库和基础文档

|项目|内容|
|---|---|
|要做什么|创建 `ai-agent-lab` 仓库，建立基础目录|
|为什么做|给长期项目建立稳定地基|
|学什么|Git、项目组织、README 结构|
|完成标准|仓库可提交，README 能说明项目定位|
|预计时间|3～5 小时|

任务清单：

```

[ ] 创建 ai-agent-lab 文件夹
[ ] git init
[ ] 创建 README.md
[ ] 创建 .gitignore
[ ] 创建 .env.example
[ ] 创建 docs/
[ ] 创建 backend/
[ ] 创建 frontend/
[ ] 写 docs/00-project-overview.md
[ ] 写 docs/01-architecture.md 初版
[ ] 第一次 commit

```

验收标准：

```

README 至少说明：
1. 项目是什么
2. 项目目标
3. 当前阶段
4. 技术栈
5. Roadmap

```

建议 commit：

```
chore: initialize ai-agent-lab project structure
```

---

## Step 2：初始化 FastAPI 后端

|项目|内容|
|---|---|
|要做什么|建立 FastAPI 项目|
|为什么做|后端是 AI Core 的入口|
|学什么|FastAPI、路由、Pydantic、CORS|
|完成标准|`/api/v1/health` 可访问|
|预计时间|5～8 小时|

任务清单：

```
[ ] 使用 uv 初始化 backend
[ ] 安装 fastapi
[ ] 安装 uvicorn
[ ] 安装 pydantic-settings
[ ] 创建 app/main.py
[ ] 创建 app/api/v1/health.py
[ ] 创建 app/core/config.py
[ ] 配置 CORS
[ ] 启动 Swagger
[ ] 测试 /api/v1/health
```

接口：

```
GET /api/v1/health
```

返回：

```json
{
  "status": "ok",
  "service": "ai-agent-lab-backend"
}
```

验收标准：

```
浏览器打开：
http://localhost:8000/docs

可以看到 Swagger。
```

建议 commit：

```
feat(backend): add FastAPI skeleton and health check
```

---

## Step 3：初始化 React 前端

|项目|内容|
|---|---|
|要做什么|建立 WebUI|
|为什么做|后续所有 Agent 能力都需要界面展示|
|学什么|React、Vite、TypeScript、Tailwind、shadcn/ui|
|完成标准|前端能启动，并显示后端连接状态|
|预计时间|6～10 小时|

任务清单：

```
[ ] 创建 Vite React TypeScript 项目
[ ] 安装 Tailwind CSS
[ ] 安装 shadcn/ui
[ ] 创建基础 Layout
[ ] 创建 ChatPage
[ ] 创建 SettingsPage
[ ] 封装 api/client.ts
[ ] 调用 /api/v1/health
[ ] 显示 Backend connected
```

验收标准：

```
前端页面显示：
Backend connected
```

建议 commit：

```
feat(frontend): add React skeleton and backend health check
```

---

## Step 4：配置环境变量

|项目|内容|
|---|---|
|要做什么|建立前后端配置系统|
|为什么做|API Key、模型地址、数据库地址都不能硬编码|
|学什么|环境变量、pydantic-settings、配置隔离|
|完成标准|`.env.example` 完整，真实 `.env` 不提交|
|预计时间|3～5 小时|

后端配置：

```
APP_NAME=AI Agent Lab
APP_ENV=development
API_V1_PREFIX=/api/v1
DATABASE_URL=sqlite:///./ai_agent_lab.db
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=
OPENROUTER_API_KEY=
OPENAI_API_KEY=
```

前端配置：

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

任务清单：

```
[ ] backend/.env.example
[ ] frontend/.env.example
[ ] 后端 config.py 读取环境变量
[ ] 前端读取 VITE_API_BASE_URL
[ ] .gitignore 排除 .env
```

验收标准：

```
真实 API Key 不进入 Git。
```

建议 commit：

```
chore: add environment configuration
```

---

## Step 5：配置 SQLite + SQLAlchemy

|项目|内容|
|---|---|
|要做什么|建立数据库基础|
|为什么做|Chat 历史、消息、模型调用都需要持久化|
|学什么|SQLAlchemy、ORM、Alembic|
|完成标准|可以创建 conversation 和 message|
|预计时间|8～12 小时|

第一版表：

```
conversations
messages
llm_calls
```

`conversations`：

```
id
title
default_provider
default_model
created_at
updated_at
```

`messages`：

```
id
conversation_id
role
content
model
provider
created_at
```

`llm_calls`：

```
id
conversation_id
message_id
provider
model
input_tokens
output_tokens
total_tokens
estimated_cost
latency_ms
status
error_message
created_at
```

任务清单：

```
[ ] 安装 SQLAlchemy
[ ] 安装 Alembic
[ ] 创建 db/session.py
[ ] 创建 db/base.py
[ ] 创建 Conversation 模型
[ ] 创建 Message 模型
[ ] 创建 LLMCall 模型
[ ] 创建 migration
[ ] 测试数据库初始化
```

验收标准：

```
后端启动后，数据库表能正常创建。
```

建议 commit：

```
feat(db): add conversation message and llm call models
```

---

## Step 6：设计 LLM Provider 抽象

|项目|内容|
|---|---|
|要做什么|定义统一模型调用接口|
|为什么做|不绑定 DeepSeek、OpenRouter 或 OpenAI|
|学什么|Provider Pattern、抽象类、异步接口、流式输出|
|完成标准|有 BaseLLMProvider 和统一数据结构|
|预计时间|8～12 小时|

核心结构：

```
ChatMessage
ChatRequest
ChatResponse
ChatChunk
TokenUsage
ModelInfo
LLMProviderError
BaseLLMProvider
```

建议接口：

```python
class BaseLLMProvider:
    async def chat(self, request: ChatRequest) -> ChatResponse:
        ...

    async def stream_chat(self, request: ChatRequest):
        ...
```

任务清单：

```
[ ] 创建 providers/llm/base.py
[ ] 定义 ChatMessage
[ ] 定义 ChatRequest
[ ] 定义 ChatResponse
[ ] 定义 ChatChunk
[ ] 定义 TokenUsage
[ ] 定义 BaseLLMProvider
[ ] 定义 Provider 错误类型
```

验收标准：

```
业务层不直接依赖某一家模型厂商 SDK。
```

建议 commit：

```
feat(llm): add base llm provider abstraction
```

---

## Step 7：实现 OpenAI-Compatible Provider

|项目|内容|
|---|---|
|要做什么|实现兼容 OpenAI 格式的模型调用|
|为什么做|DeepSeek、OpenRouter、很多国产模型都支持 OpenAI-compatible 格式|
|学什么|Chat Completions、SSE、超时、重试、错误处理|
|完成标准|可以调用真实模型|
|预计时间|10～16 小时|

任务清单：

```
[ ] 创建 openai_compatible.py
[ ] 支持 base_url
[ ] 支持 api_key
[ ] 支持 model
[ ] 支持 messages
[ ] 支持 temperature
[ ] 支持 max_tokens
[ ] 支持非流式 chat
[ ] 支持流式 stream_chat
[ ] 解析 usage
[ ] 统一错误处理
```

验收标准：

```
后端脚本可以成功调用 DeepSeek 或 OpenRouter。
```

建议 commit：

```
feat(llm): implement openai compatible provider
```

---

## Step 8：实现 Model Registry

|项目|内容|
|---|---|
|要做什么|建立模型注册表|
|为什么做|前端选择模型、后端路由模型、成本统计都依赖它|
|学什么|配置驱动、模型能力标签、模型元数据|
|完成标准|前端能读取模型列表|
|预计时间|5～8 小时|

`models.yaml` 示例：

```yaml
models:
  - provider: deepseek
    model: deepseek-chat
    display_name: DeepSeek Chat
    supports_streaming: true
    supports_tools: true
    supports_json: true
    input_price_per_1m: 0
    output_price_per_1m: 0

  - provider: openrouter
    model: openai/gpt-4o-mini
    display_name: GPT-4o Mini via OpenRouter
    supports_streaming: true
    supports_tools: true
    supports_json: true
    input_price_per_1m: 0
    output_price_per_1m: 0
```

任务清单：

```
[ ] 创建 models.yaml
[ ] 创建 registry.py
[ ] 读取模型配置
[ ] 创建 GET /api/v1/models
[ ] 前端模型选择器读取模型列表
```

验收标准：

```
页面可以看到模型下拉框。
```

建议 commit：

```
feat(llm): add model registry
```

---

## Step 9：实现 Chat API

|项目|内容|
|---|---|
|要做什么|建立后端 Chat 接口|
|为什么做|这是整个系统最核心 API|
|学什么|API 设计、Pydantic、Service 层、数据库写入|
|完成标准|Swagger 里可以完成一次聊天|
|预计时间|8～12 小时|

接口：

```
POST /api/v1/chat/completions
POST /api/v1/chat/stream
```

请求：

```json
{
  "conversation_id": null,
  "provider": "deepseek",
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "user",
      "content": "你好，介绍一下 AI Agent Lab"
    }
  ],
  "stream": true
}
```

任务清单：

```
[ ] 创建 schemas/chat.py
[ ] 创建 api/v1/chat.py
[ ] 创建 chat_service.py
[ ] 支持创建新 conversation
[ ] 保存用户消息
[ ] 调用 LLM Provider
[ ] 保存 assistant 消息
[ ] 保存 llm_call 记录
[ ] 返回 conversation_id
```

验收标准：

```
Swagger 可以调用接口并得到模型回答。
```

建议 commit：

```
feat(chat): add chat completion api
```

---

## Step 10：实现 Streaming Chat

|项目|内容|
|---|---|
|要做什么|后端 SSE 流式输出，前端流式渲染|
|为什么做|流式输出是 AI Chat 基础体验|
|学什么|SSE、异步生成器、ReadableStream、AbortController|
|完成标准|前端可以逐字/逐段显示模型输出|
|预计时间|10～16 小时|

任务清单：

```
[ ] 后端实现 SSE response
[ ] 后端逐 chunk 返回
[ ] 前端 fetch stream 读取
[ ] 前端边接收边渲染
[ ] 支持生成中状态
[ ] 支持停止生成按钮雏形
[ ] 网络错误时显示错误
```

验收标准：

```
不是等模型完整回答后一次性显示，而是流式显示。
```

建议 commit：

```
feat(chat): add streaming chat support
```

---

## Step 11：实现前端 Chat UI

|项目|内容|
|---|---|
|要做什么|做出基础聊天界面|
|为什么做|需要可展示、可调试、可作为作品集截图|
|学什么|React 组件、状态管理、Markdown 渲染|
|完成标准|可以像普通 Chat 应用一样使用|
|预计时间|12～20 小时|

组件：

```
ChatPage
ConversationSidebar
MessageList
MessageItem
MessageInput
ModelSelector
ChatHeader
```

任务清单：

```
[ ] 左侧会话列表
[ ] 中间消息区
[ ] 底部输入框
[ ] 顶部模型选择器
[ ] 用户消息展示
[ ] assistant 消息展示
[ ] Markdown 渲染
[ ] loading 状态
[ ] error 状态
[ ] 新建会话按钮
```

验收标准：

```
可以打开网页，选择模型，发送消息，看到流式回复。
```

建议 commit：

```
feat(frontend): add basic chat interface
```

---

## Step 12：实现会话历史

|项目|内容|
|---|---|
|要做什么|保存和加载历史会话|
|为什么做|没有历史记录就只是 Demo|
|学什么|会话模型、API 分页、前端状态管理|
|完成标准|刷新页面后历史还在|
|预计时间|8～12 小时|

接口：

```
GET /api/v1/conversations
GET /api/v1/conversations/{conversation_id}
GET /api/v1/conversations/{conversation_id}/messages
POST /api/v1/conversations
DELETE /api/v1/conversations/{conversation_id}
```

任务清单：

```
[ ] 创建 conversations.py
[ ] 实现会话列表接口
[ ] 实现会话详情接口
[ ] 实现消息列表接口
[ ] 前端加载会话列表
[ ] 点击会话加载消息
[ ] 新建会话
[ ] 删除会话，先可选
```

验收标准：

```
刷新浏览器后，会话记录仍然存在。
```

建议 commit：

```
feat(chat): add conversation history
```

---

## Step 13：实现 Token / Cost / Latency 统计

|项目|内容|
|---|---|
|要做什么|记录每次模型调用的基础指标|
|为什么做|成本意识和可观测性从第一阶段就要建立|
|学什么|usage 解析、模型价格配置、延迟统计|
|完成标准|每条 assistant 消息有调用统计|
|预计时间|6～10 小时|

任务清单：

```
[ ] 记录 started_at
[ ] 记录 ended_at
[ ] 计算 latency_ms
[ ] 从 provider response 解析 usage
[ ] 保存 input_tokens
[ ] 保存 output_tokens
[ ] 保存 total_tokens
[ ] 根据模型价格估算 cost
[ ] 前端展示本轮调用统计
```

验收标准：

```
每次回答下面能看到：
model / latency / token / estimated cost
```

建议 commit：

```
feat(observability): add basic llm usage tracking
```

---

## Step 14：实现基础错误处理

|项目|内容|
|---|---|
|要做什么|统一处理模型调用和 API 错误|
|为什么做|模型接口经常出错，不处理会非常脆弱|
|学什么|异常分类、HTTP 状态码、前端错误展示|
|完成标准|API Key 错误、超时、限流都有提示|
|预计时间|6～10 小时|

错误类型：

```
ProviderAuthError
ProviderRateLimitError
ProviderTimeoutError
ProviderBadRequestError
ProviderServerError
ProviderUnknownError
```

任务清单：

```
[ ] 定义统一错误类
[ ] Provider 内部捕获 HTTP 错误
[ ] API 返回标准错误格式
[ ] 前端展示错误信息
[ ] 日志记录错误堆栈
[ ] 不打印 API Key
```

验收标准：

```
即使 API Key 错误，服务也不会崩。
```

建议 commit：

```
fix(llm): add provider error handling
```

---

## Step 15：实现基础日志

|项目|内容|
|---|---|
|要做什么|建立后端日志系统|
|为什么做|后续 Agent、Tool、RAG 都需要日志|
|学什么|logging、request_id、错误堆栈|
|完成标准|每次请求和错误都有日志|
|预计时间|4～8 小时|

任务清单：

```
[ ] 创建 core/logging.py
[ ] 设置日志格式
[ ] 增加 request_id
[ ] 记录请求路径
[ ] 记录错误堆栈
[ ] 确保不输出敏感信息
```

验收标准：

```
控制台能看到结构清晰的请求日志和错误日志。
```

建议 commit：

```
chore: add backend logging
```

---

## Step 16：补充基础测试

|项目|内容|
|---|---|
|要做什么|给关键模块写最小测试|
|为什么做|AI 生成代码容易看起来能跑，但边界错误很多|
|学什么|pytest、API 测试、单元测试|
|完成标准|核心接口有测试|
|预计时间|8～12 小时|

测试范围：

```
[ ] /health 测试
[ ] model registry 测试
[ ] conversation 创建测试
[ ] message 保存测试
[ ] provider request 构造测试
[ ] chat api 基础测试
```

验收标准：

```
pytest 能跑通。
```

建议 commit：

```
test: add basic backend tests
```

---

## Step 17：写 Plan 1 文档

|项目|内容|
|---|---|
|要做什么|写清楚第一阶段设计|
|为什么做|这个项目是学习型参考实现，文档本身就是成果|
|学什么|技术文档写作、架构表达|
|完成标准|docs 下有 Plan 1 相关文档|
|预计时间|6～10 小时|

文档：

```
docs/02-plan-1-foundation.md
docs/03-llm-provider.md
docs/04-chat-api.md
docs/05-frontend-chat-ui.md
```

每篇文档写：

```
1. 模块目标
2. 为什么这么设计
3. 核心数据结构
4. API 说明
5. 当前限制
6. 后续扩展
```

验收标准：

```
别人看文档能理解 Plan 1 怎么实现。
```

建议 commit：

```
docs: add plan 1 foundation documents
```

---

## Step 18：Plan 1 封版

|项目|内容|
|---|---|
|要做什么|固化 v0.1.0 版本|
|为什么做|长期项目必须有里程碑版本|
|学什么|Git tag、版本管理、Demo 记录|
|完成标准|v0.1.0 可运行、可展示|
|预计时间|3～5 小时|

任务清单：

```
[ ] 更新 README
[ ] 写 CHANGELOG.md
[ ] 截图 Chat UI
[ ] 记录当前功能
[ ] 记录已知问题
[ ] 创建 tag v0.1.0
```

验收标准：

```
从 README 能启动项目，并完成一次聊天。
```

建议 commit：

```
chore: release v0.1.0 foundation chat
```

---

## 6. Plan 1 里程碑拆分

为了防止你一口气做太大，Plan 1 再拆成 4 个小里程碑。

|小里程碑|名称|内容|预计时间|
|---|---|---|---|
|M1|工程骨架|Git、FastAPI、React、环境变量、健康检查|15～25 h|
|M2|数据与 Provider|SQLite、SQLAlchemy、LLM Provider、OpenAI-compatible|25～40 h|
|M3|Chat 闭环|Chat API、Streaming、前端 Chat UI、会话历史|25～40 h|
|M4|工程补强|Token/Cost、错误处理、日志、测试、文档、封版|20～35 h|

---

## 7. Plan 1 最终验收标准

Plan 1 完成后，必须满足：

```
[ ] 后端能启动
[ ] 前端能启动
[ ] 前端能调用后端 health API
[ ] 能配置 DeepSeek 或 OpenRouter API Key
[ ] 能选择模型
[ ] 能发送消息
[ ] 能流式输出
[ ] 能保存会话
[ ] 刷新页面后历史会话还在
[ ] 能记录 provider / model / latency / token / cost
[ ] API Key 错误时不会崩溃
[ ] README 有启动说明
[ ] docs 有第一阶段设计文档
[ ] 有 v0.1.0 tag
```

---

## 8. Plan 1 的最小可交付版本

如果你中途时间不够，Plan 1 可以砍到这个最小版本：

```text
1. FastAPI 后端
2. React 前端
3. /health
4. OpenAI-compatible Provider
5. DeepSeek 或 OpenRouter 接入
6. Chat API
7. Streaming
8. Chat UI
9. SQLite 保存会话
10. README
```

可以暂时延后：

```
1. 成本统计
2. 完整错误分类
3. 删除会话
4. 前端美化
5. 完整测试
```

但不能延后：

```
1. Provider 抽象
2. Streaming
3. 会话保存
4. README
```

如果按最小版本进入 Plan 2，必须先补齐以下桥接项：

```text
1. LLM Provider 的 chat 接口稳定，后续可以扩展 tools 参数
2. Message / Conversation 数据模型稳定，Agent Run 可以引用会话上下文
3. Streaming Chat 不阻塞普通 Chat API
4. 基础日志可定位 provider、model、latency 和错误原因
5. README 能让开发者从零启动前端和后端
```

---

## 9. Plan 1 与 Plan 2 的衔接

Plan 1 完成后，项目具备：

```text
基础 Chat 能力
多模型 Provider
Streaming
会话历史
模型选择
Token / Cost / Latency 基础记录
基础日志和错误处理
```

这为 Plan 2 的 Tool Calling 和简单 Agent Loop 打基础。

Plan 2 不需要重写 Chat 系统，而是在 Plan 1 的 Provider、Chat API 和会话系统之上增加：

```text
Tool 抽象
Tool Registry
工具参数校验
工具执行记录
Simple Agent Loop
前端 Tool Call 展示
```

Plan 1 的目标不是做完整 Agent，而是把后续 Agent 可以复用的工程地基打稳。

---

## 10. Plan 1 实施建议

Plan 1 最容易犯的错误是过早追求完整产品体验。

推荐执行顺序：

```text
先跑通后端和前端
再跑通 LLM Provider
再做 Chat API 和 Streaming
再做会话保存
最后补 Token / Cost / Latency、错误处理、日志和文档
```

不要在 Plan 1 阶段提前做 RAG、Agent、Memory 或复杂 UI。

Plan 1 的关键是形成一个稳定、可启动、可扩展的 Web Chat 底座。只要这个底座稳，Plan 2～Plan 6 都可以自然往上长。
