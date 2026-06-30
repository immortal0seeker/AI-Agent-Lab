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

第一批实现范围限制为 `P1-M1-S1` 到 `P1-M1-S3`。

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

后端和前端会按阶段逐步搭建。具体启动命令会在对应的 Plan 1 Step 创建可运行服务后补充。

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
