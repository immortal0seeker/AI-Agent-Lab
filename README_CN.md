# AI Agent Lab

[English](README.md) | [中文](README_CN.md)

AI Agent Lab 是一个分阶段构建的 AI Engineering Workspace，用来学习和实践现代 AI 应用背后的核心系统。项目从稳定的 FastAPI + React 工程底座开始，逐步扩展到 Chat、Provider 抽象、Tool Calling、RAG、Trace、Memory、Agent Runtime、MCP、Voice、Vision 和 Desktop 工作流。

这个仓库不是一组互不相干的 Demo。目标是按计划一步一步构建一个可使用、可观测、可测试、可扩展的 AI 工程工作台。

## 当前阶段

当前版本：`v0.1.0`（Plan 1 工程底座）。

Plan 1 覆盖：

- 项目基础骨架
- FastAPI 后端骨架
- React + TypeScript 前端骨架
- 基础健康检查
- 基础 Chat 流程
- LLM Provider 抽象
- OpenAI-compatible Provider 支持
- Streaming Chat
- 会话历史
- 基础 token、cost、latency、logging 和 error handling

已完成范围：`P1-M1-S1` 到 `P1-M4-S8`。

当前开发阶段：Plan 2 M2 已完成。已完成的 Plan 2 范围为 `P2-M1-S1` 到
`P2-M2-S7`。

M1 地基包括 Tool 与 ToolResult 契约、ToolCall 传输 schema、有序 Tool
Registry、Draft 2020-12 参数校验、只读路径策略，以及 AgentRun/ToolCall ORM
模型与 Alembic 迁移。M2 新增并注册 `read_file` 与 `list_dir` 两个只读内置
Tool，具备有界 I/O、工作区相对路径策略、敏感名称过滤、安全失败结果和 Mock
回归覆盖。`P2-M2-S7` 已完成 `web_fetch` 评估并明确延期：可信网络 Tool 需要
完整处理 SSRF、DNS/重定向、超时、响应大小、内容类型和正文提取边界。当前没有
实现、注册或暴露 `web_fetch` Tool/schema。Provider tool calling、Agent Loop、
Agent API 和前端 Agent/ToolCall 视图仍未实现。

下一批：`P2-M3-S1` 到 `P2-M3-S3`。

## v0.1.0 演示

![桌面端 Chat 工作台](docs/assets/plan1/chat-workspace-desktop.png)

![移动端 Chat 工作台](docs/assets/plan1/chat-workspace-mobile.png)

以上均为脱敏 Mock 演示。生成过程没有使用真实 Provider、真实 API Key 或
用户本地会话数据库。

## Plan 1 非目标

Plan 1 不实现：

- Tool Calling
- RAG
- Memory
- MCP
- Voice
- Vision
- Desktop app
- Multi-agent workflows

这些能力会按计划延后到后续阶段。

## 计划技术栈

- 后端：Python 3.11、FastAPI、Pydantic、SQLAlchemy、SQLite
- 前端：React、Vite、TypeScript
- LLM 接入：OpenAI-compatible providers，例如 DeepSeek 或 OpenRouter
- 测试：后端使用 pytest，前端使用 TypeScript/build 检查

本工作台以本地优先、单用户使用为主要定位。SQLite 是默认且长期支持的主数据库，
不是迁移到 PostgreSQL 之前的临时方案。SQLAlchemy 和 Alembic 用于保留合理的数据库
可移植性；只有部署或并发需求发生实质变化时，才重新评估 PostgreSQL 兼容路径。

## 仓库结构

```text
AI-Agent-Lab/
├── backend/       # FastAPI 后端，在 Plan 1 中逐步补齐
├── frontend/      # React + TypeScript 前端，在 Plan 1 中逐步补齐
├── docs/          # 已跟踪的正式项目文档和已脱敏资产
├── docs-plan/     # 已跟踪的计划源文档和执行步骤表
├── docs-local/    # 已忽略的本地草稿、私有笔记和敏感材料
├── AGENTS.md      # 根级英文协作规范
├── AGENTS_CN.md   # 根级中文协作规范
├── .env.example   # 根级环境变量示例
└── .gitignore
```

## 文档目录边界

- `docs-plan/` 存放计划源文档和执行步骤表。该目录需要提交到 Git。
- `docs/` 存放正式项目文档和已脱敏的验证资产。该目录需要提交到 Git。
- `docs-local/` 存放本地草稿、私有笔记、临时 review 材料和敏感截图。该目录会被忽略，不应提交。

## 本地开发

Plan 1 后端和前端可以分别启动。根目录 `.env.example` 只是工作区级参考，
当前后端和前端都不会自动加载它。如需本地覆盖配置，请复制各服务自己的示例：

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

从 `backend/` 运行的后端命令读取 `backend/.env`；从 `frontend/` 运行的 Vite
命令读取 `frontend/.env`。这些本地文件必须保持未跟踪。已跟踪示例不包含真实凭据；
`VITE_*` 变量会暴露到浏览器，因此绝不能保存秘密。

### 后端

```bash
py -3.11 -m venv .venv
cd backend
..\.venv\Scripts\python.exe -m pip install -e .[dev] --no-build-isolation
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

后端默认数据库为 `sqlite:///./ai_agent_lab.db`。如需调整，请通过本地未跟踪的
环境变量设置 `DATABASE_URL`。数据库结构由 Alembic 管理，目前会创建
`conversations`、`messages` 和 `llm_calls`；应用启动时不会自动建表。

OpenAI-compatible Provider 在初始化时读取以下可选环境变量：

```text
OPENAI_COMPATIBLE_BASE_URL=https://api.example.com/v1
OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_MODEL=example-model
OPENAI_COMPATIBLE_TIMEOUT_SECONDS=30
```

真实值只能放在本地未跟踪的 `.env` 或环境变量中。应用仅提供 health 流程时，
没有 API Key 也可以启动；真正初始化 Provider 时若缺少 Key，会返回可读配置错误。
Batch 5 使用 mock HTTP 测试，没有连接真实模型服务。

JSON Model Registry 位于 `backend/app/providers/llm/models.json`。其中的
已跟踪条目只是示例配置。单元测试覆盖 Registry 加载、筛选、查询、重复项检测和
严格元数据校验。Provider 与 Registry 边界见 `docs/03-llm-provider.md`。

非流式和 SSE Chat 后端流程已经建立：

```text
POST /api/v1/conversations
GET  /api/v1/conversations
GET  /api/v1/conversations/{conversation_id}
GET  /api/v1/conversations/{conversation_id}/messages
GET  /api/v1/models
POST /api/v1/chat/completions
POST /api/v1/chat/stream
```

Chat 接口只接收本轮新的用户 `content`。后端负责加载数据库会话历史、校验
Registry 模型、调用已配置 Provider，并在一个事务中写入用户消息、assistant
消息和成功的 `LLMCall`。SSE 接口先发送 `delta` 事件，再发送一个 `done`
事件；成功流在 `done` 前提交，Provider 失败或客户端取消会回滚本轮全部记录。
测试只使用 mock Provider。

新会话首个成功用户回合会在规范化空白后生成最多 50 个字符的标题。成功回合还会
记录该会话最后使用的 Registry 模型并更新活动时间。会话和消息列表接口用于最近
历史导航；失败或取消的回合不会更新这些元数据。

非流式和流式成功回合现在会把 Provider usage、基于 Registry 价格估算的 cost 和
Provider latency 写入 `LLMCall`。usage 缺失或任一 Registry 价格未知时保持
`null`，后端不会猜测数值。HTTP 与 SSE 错误使用安全的结构化 envelope，并通过
服务端生成的 `X-Request-ID` 关联日志。请求和模型调用日志包含 request ID、
provider/model、outcome 和 latency，但不记录完整消息、凭据、上游错误正文或 SQL
参数。

健康检查：

```text
GET http://localhost:8000/api/v1/health
```

预期响应：

```json
{
  "status": "ok",
  "service": "ai-agent-lab-backend"
}
```

后端验证：

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

打开 `npm run dev` 输出的 Vite 地址。首屏是可用的 Chat 工作台，包含 API
健康状态、当前模型信息、消息状态、流式输出、Stop 和 New Chat 控件。前端读取
以下安全默认值：

```text
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_DEFAULT_PROVIDER=openai_compatible
VITE_DEFAULT_MODEL=example-model
```

API 区域显示 `Checking API`、`API connected` 或 `API unavailable`。
模型和最近会话加载期间会显示独立的工作区初始化状态；初始化失败时只显示一条
可读错误和 `Retry` 按钮，成功重试后恢复 ready 状态，不会启动自动重试循环。
工作区 ready 后，Chat 覆盖空白、会话加载、生成中、成功、已停止和错误状态。
模型选择器从 `GET /api/v1/models` 加载，侧栏显示最近会话并加载持久化消息。
当前会话写入 `?conversation=<uuid>`，刷新后会恢复其消息和最后成功使用的模型。
停止生成会在前端保留已有部分文本，但不会持久化被中断的本轮消息。迟到的历史
消息和会话列表刷新响应不会覆盖较新状态；终止 SSE 错误也会主动释放响应 reader。

前端检查：

```powershell
cd frontend
npm run typecheck
npm run test
npm run build
```

封版文档：

- [CHANGELOG](CHANGELOG.md)
- [Plan 1 工程底座封版说明](docs/02-plan-1-foundation.md)
- [架构说明](docs/01-architecture.md)
- [LLM Provider 与 Model Registry](docs/03-llm-provider.md)
- [Tool Calling 设计](docs/10-tool-calling-design.md)
- [Plan 1 最终复审记录](docs/reviews/2026-07-13-plan1-v0.1.0-final-review.md)
- `docs-plan/00-ALL PLAN/01-PLAN-1 (V1.0).md`
- `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

## 当前限制

封版验证只使用 Mock Provider，不能证明真实 DeepSeek/OpenRouter 已连通。
Token、预估成本和延迟保存在后端 `LLMCall` 中，但当前前端尚不展示。
当前 editable install 工作流也没有把 `models.json` 声明为未来 wheel/sdist
的 package data。Provider retry/fallback、失败调用审计记录、会话管理扩展、
Markdown 渲染以及后续 Plan 能力仍然延后。完整限制见
[Plan 1 工程底座封版说明](docs/02-plan-1-foundation.md)。

## Roadmap

- Plan 1：项目骨架 + 基础 Chat + LLM Providers
- Plan 2：Tool Calling + 简单 Agent Loop
- Plan 3：Knowledge Base + Document Ingestion + Naive RAG
- Plan 4：Trace + Advanced RAG + Rerank + Evaluation
- Plan 5：Memory + Context Engine + Agent Runtime + Human Approval
- Plan 6：MCP + Voice + Vision + Desktop
