# AI Agent Lab

[English](README.md) | [中文](README_CN.md)

AI Agent Lab 是一个分阶段构建的 AI Engineering Workspace，用来学习和实践现代 AI 应用背后的核心系统。项目从稳定的 FastAPI + React 工程底座开始，逐步扩展到 Chat、Provider 抽象、Tool Calling、RAG、Trace、Memory、Agent Runtime、MCP、Voice、Vision 和 Desktop 工作流。

这个仓库不是一组互不相干的 Demo。目标是按计划一步一步构建一个可使用、可观测、可测试、可扩展的 AI 工程工作台。

## 当前阶段

当前计划：Plan 1，目标版本 `v0.1.0`。

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

已完成范围：`P1-M1-S1` 到 `P1-M2-S8`。

下一批范围：`P1-M3-S1` 到 `P1-M3-S3`。

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

后端和前端会按阶段逐步搭建。Milestone 1 现在支持本地启动前后端，并能从前端首页验证后端健康检查接口。

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

```bash
cd backend
..\.venv\Scripts\python.exe -m pytest -q
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

打开 `npm run dev` 输出的 Vite 地址。首页会显示当前配置的
`VITE_API_BASE_URL`，并展示以下健康状态之一：

- `Checking health...`：前端正在调用后端健康检查。
- `Backend healthy`：`GET /api/v1/health` 调用成功。
- `Backend error`：后端不可达或返回错误状态。

前端检查：

```bash
npm run typecheck
npm run test
npm run build
```

Batch 6 提交说明：用户在确认已验证 diff 后手动创建 Git commit。建议 commit message：

```text
feat(llm): add model registry and provider docs
```

当前请以计划文档作为执行依据：

- `docs-plan/00-ALL PLAN/01-PLAN-1 (V1.0).md`
- `docs-plan/01-PLAN1/01-PLAN1-执行步骤表 (V1.0).md`

## Roadmap

- Plan 1：项目骨架 + 基础 Chat + LLM Providers
- Plan 2：Tool Calling + 简单 Agent Loop
- Plan 3：Knowledge Base + Document Ingestion + Naive RAG
- Plan 4：Trace + Advanced RAG + Rerank + Evaluation
- Plan 5：Memory + Context Engine + Agent Runtime + Human Approval
- Plan 6：MCP + Voice + Vision + Desktop
