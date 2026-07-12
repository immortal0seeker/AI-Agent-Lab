# Plan 1 执行步骤表｜项目骨架 + 基础 Chat

> 适用文档：`00-ALL PLAN/01-PLAN-1 (V1.0).md`  
> 执行方式：每次只领取连续 1～3 个 Step，完成后立即测试、提交、review。  
> 阶段目标：一个阶段完成一个里程碑；一个里程碑通过后再进入下一个里程碑。

---

## 0. 执行总原则

| 规则 | 说明 |
|---|---|
| 单次执行范围 | Cursor / Codex 每次只做 1～3 个连续 Step |
| 执行顺序 | 必须按 `P1-Mx-Sy` 顺序推进，除非 Codex 明确调整 |
| 每步完成定义 | 代码可运行、局部测试通过、相关文档或配置同步 |
| 每个阶段完成定义 | 阶段验收项全部通过，Codex review 后进入下一阶段 |
| Claude Code 使用时机 | M2 已完成二审；下一次集中二审放在 M4 结束后 |
| 提交节奏 | 每 1～3 个 Step 一次 commit；每个里程碑结束一次 review commit |
| 文档同步 | 接口、环境变量、启动方式、目录结构变化必须同步 README 或 docs |
| 禁止提前做 | Tool Calling、RAG、Memory、MCP、语音、多模态、桌面端 |

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

## 1. Plan 1 总览

| 阶段 | 里程碑 | 对应原 PLAN1 Step | 核心交付 | 预计时间 | 主要工具 | 审核节点 |
|---|---|---|---|---:|---|---|
| Phase 1 | M1 工程骨架 | Step 1～4 | 仓库、后端、前端、环境变量、健康检查 | 15～25 h | Codex + Cursor | Codex review |
| Phase 2 | M2 数据与 Provider | Step 5～8 | SQLite、SQLAlchemy、LLM Provider、Model Registry | 25～40 h | Codex | Codex + Claude Code |
| Phase 3 | M3 Chat 闭环 | Step 9～12 | Chat API、Streaming、Chat UI、会话历史 | 25～40 h | Codex + Cursor | Codex + Claude Code |
| Phase 4 | M4 工程补强与封版 | Step 13～18 | Token / Cost / Latency、错误处理、日志、测试、文档、v0.1.0 | 20～35 h | Codex + Cursor | Codex + Claude Code |

---

## 2. 执行节奏表

| 执行批次 | 建议领取范围 | 批次目标 | 完成后动作 | 状态 |
|---|---|---|---|---|
| Batch 1 | P1-M1-S1～S3 | 建立仓库和后端最小可运行骨架 | 启动后端，提交基础骨架 | 已完成 |
| Batch 2 | P1-M1-S4～S6 | 建立前端和环境变量规范 | 启动前端，验证 health 调用 | 已完成 |
| Batch 3 | P1-M1-S7～S8 | 打通前后端基础联通和文档 | Codex review M1 | 已完成 |
| Batch 4 | P1-M2-S1～S3 | 建立数据库、ORM、迁移基础 | 跑数据库测试 | 已完成 |
| Batch 5 | P1-M2-S4～S6 | 建立 LLM Provider 抽象和 OpenAI-compatible Provider | mock provider 测试 | 已完成 |
| Batch 6 | P1-M2-S7～S8 | 建立 Model Registry 和 provider 配置 | Codex + Claude review M2 | 已完成 |
| Batch 7 | P1-M3-S1～S3 | 实现非流式 Chat API | 后端 chat 测试 | 已完成 |
| Batch 8 | P1-M3-S4～S6 | 实现 Streaming Chat 和前端基础 Chat UI | 浏览器手测流式输出 | 已完成 |
| Batch 9 | P1-M3-S7～S9 | 实现会话历史和刷新恢复 | Codex review M3 | 未完成 |
| Batch 10 | P1-M4-S1～S3 | 实现 token / cost / latency 和错误处理 | 后端测试 | 未完成 |
| Batch 11 | P1-M4-S4～S6 | 实现日志、基础测试、文档 | 全量测试 | 未完成 |
| Batch 12 | P1-M4-S7～S8 | 封版、截图、CHANGELOG、tag | Codex + Claude final review | 未完成 |

---

## 3. Phase 1｜M1 工程骨架

阶段目标：

```text
仓库结构稳定，前后端都能启动，后端 health API 可用，前端可以访问后端。
```

阶段验收：

```text
1. backend 可以启动 FastAPI
2. frontend 可以启动 React / Vite
3. GET /api/v1/health 返回 ok
4. 前端能显示后端健康状态
5. README 写清楚本地启动方式
```

文档目录边界：

```text
docs-plan/  保存计划源文档和执行步骤表，必须提交
docs/       保存正式项目文档和已脱敏验收材料，必须提交
docs-local/ 保存本地草稿、未脱敏截图、临时 review 和敏感调试记录，必须忽略
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P1-M1-S1 | 创建仓库根目录、`.gitignore`、`README.md`、`.env.example`、`docs/`、`docs-local/`、`backend/`、`frontend/` | Codex | 基础目录和说明文件；`docs-local/` 已被 `.gitignore` 忽略 | `git status` 能看到预期文件，且不显示 `docs-local/` 内容 | Codex |
| P1-M1-S2 | 写 `docs/00-project-overview.md` 和 `docs/01-architecture.md` 初版 | Codex | 项目定位、第一阶段架构说明 | 文档能说明 Plan 1 范围和非目标 | Codex |
| P1-M1-S3 | 初始化 FastAPI 项目，创建 `backend/app/main.py` 和 `GET /api/v1/health` | Codex | 后端最小服务 | `uvicorn app.main:app --reload` 后访问 health | Codex |
| P1-M1-S4 | 配置后端 `pyproject.toml`、基础依赖、`backend/.env.example` | Codex | 后端依赖和环境变量样例 | 后端能从空环境按 README 启动 | Codex |
| P1-M1-S5 | 初始化 React + Vite + TypeScript 前端 | Cursor | `frontend/` 可启动 | `npm run dev` 能打开页面 | Cursor 自查 |
| P1-M1-S6 | 配置前端 API client 和 `.env.example` | Cursor | `frontend/src/api/client.ts` | 前端能读取后端 base URL | Codex |
| P1-M1-S7 | 实现前端 Health 状态展示 | Cursor | App 首页或基础布局展示 API 状态 | 页面显示 backend healthy / error | Codex |
| P1-M1-S8 | 补充 M1 README 启动说明和第一批 commit | Codex | README、本阶段 commit | 新环境按 README 可启动前后端 | Codex review |

M1 完成后建议 commit：

```text
chore: scaffold ai agent lab foundation
```

---

## 4. Phase 2｜M2 数据与 Provider

阶段目标：

```text
建立 SQLite 数据层、LLM Provider 抽象、OpenAI-compatible Provider 和 Model Registry。
```

数据库策略：SQLite 是本地优先、单用户工作台默认且长期支持的主数据库；PostgreSQL 仅保留技术兼容能力，不作为 M2 或 Plan 1 之后的必然迁移任务。

阶段验收：

```text
1. SQLite 可用
2. SQLAlchemy session 可用
3. Conversation / Message / LLMCall 模型可用
4. LLMProvider 抽象稳定
5. OpenAI-compatible Provider 可通过配置调用 DeepSeek 或 OpenRouter
6. Model Registry 能列出可用模型和能力标签
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P1-M2-S1 | 配置 SQLAlchemy session、Base、Alembic | Codex | `backend/app/db/session.py`、`base.py`、迁移配置 | 能创建 SQLite 数据库 | Codex |
| P1-M2-S2 | 创建 `Conversation`、`Message`、`LLMCall` ORM 模型 | Codex | `backend/app/models/*.py` | ORM 测试能创建和查询记录 | Codex |
| P1-M2-S3 | 创建 conversation / message / llm_call schemas | Codex | `backend/app/schemas/*.py` | Pydantic schema 单测通过 | Codex |
| P1-M2-S4 | 设计 `LLMProvider` 抽象和 `LLMResponse` 数据结构 | Codex | `providers/llm/base.py` | mock provider 测试通过 | Claude Code 可审 |
| P1-M2-S5 | 实现 OpenAI-compatible Provider | Codex | `providers/llm/openai_compatible.py` | 使用 mock HTTP 或手动配置验证 | Codex |
| P1-M2-S6 | 增加 provider 配置读取和 API Key 缺失处理 | Codex | `core/config.py`、provider 初始化逻辑 | 缺少 key 时返回可读错误 | Codex |
| P1-M2-S7 | 实现 Model Registry | Codex | `providers/llm/registry.py`、模型能力标签 | API 或测试能列出模型 | Codex |
| P1-M2-S8 | 补充 M2 单元测试和 Provider 文档 | Codex | tests、`docs/03-llm-provider.md` | provider / registry 测试通过 | Codex + Claude review |

M2 完成后建议 commit：

```text
feat: add database models and llm provider layer
```

---

## 5. Phase 3｜M3 Chat 闭环

阶段目标：

```text
实现从前端发送消息到后端调用模型、流式返回、保存会话和刷新恢复的完整 Chat 闭环。
```

阶段验收：

```text
1. 可以创建或继续一个会话
2. 可以选择 provider / model
3. 普通 Chat API 可返回模型回答
4. Streaming Chat 可逐步输出
5. 前端 Chat UI 可展示 user / assistant 消息
6. 刷新页面后历史会话仍可查看
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P1-M3-S1 | 实现 Conversation Service | Codex | `services/conversation_service.py` | 创建、查询、追加消息测试通过 | Codex |
| P1-M3-S2 | 实现非流式 Chat Service | Codex | `services/chat_service.py` | mock provider chat 测试通过 | Codex |
| P1-M3-S3 | 实现 Chat API 和 Conversations API | Codex | `api/v1/chat.py`、`conversations.py` | OpenAPI 可见，接口测试通过 | Codex |
| P1-M3-S4 | 实现 Streaming Chat SSE | Codex | streaming endpoint | curl 或浏览器能看到分段输出 | Codex |
| P1-M3-S5 | 创建前端 Chat 类型、API 封装和 Zustand store | Cursor | `types/chat.ts`、`api/chat.ts`、`stores/chatStore.ts` | TypeScript 检查通过 | Codex |
| P1-M3-S6 | 实现基础 Chat UI | Cursor | `ChatPage.tsx`、消息列表、输入框、发送按钮 | 页面可发送消息并展示回答 | Codex |
| P1-M3-S7 | 实现模型选择和会话列表 | Cursor | Model selector、Conversation sidebar | 能切换模型和选择历史会话 | Codex |
| P1-M3-S8 | 实现会话刷新恢复 | Cursor + Codex | 前端加载历史会话，后端返回消息列表 | 刷新页面后消息仍在 | Codex |
| P1-M3-S9 | 补充 Chat API、Streaming、Conversation 测试 | Codex | 后端测试、必要的前端 smoke 测试 | 测试通过 | Codex |

M3 完成后建议 commit：

```text
feat: implement chat api streaming ui and conversation history
```

---

## 6. Phase 4｜M4 工程补强与封版

阶段目标：

```text
补齐 Plan 1 作为长期项目底座必须有的工程能力：成本统计、错误处理、日志、测试、文档、截图、CHANGELOG、v0.1.0 tag。
```

阶段验收：

```text
1. 能记录 provider / model / latency / token / cost
2. API Key 错误、Provider 错误、数据库错误不会导致服务崩溃
3. 后端基础测试通过
4. 前端构建通过
5. README 和 docs 足够让别人启动项目
6. CHANGELOG 记录 v0.1.0
7. 创建 v0.1.0 tag
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P1-M4-S1 | 实现 Token / Cost / Latency 记录 | Codex | `LLMCall` 写入统计字段 | 调用一次 chat 后数据库有记录 | Codex |
| P1-M4-S2 | 实现基础错误分类和统一 API 错误返回 | Codex | `core/errors.py`、异常处理器 | 模拟 provider error 返回可读错误 | Codex |
| P1-M4-S3 | 实现基础日志 | Codex | `core/logging.py`、请求/模型调用日志 | 运行 chat 时日志包含 request_id / model / latency | Codex |
| P1-M4-S4 | 补充后端测试 | Codex | health、provider、chat、conversation、error 测试 | `pytest` 通过 | Codex |
| P1-M4-S5 | 补充前端检查和基础 UI 修正 | Cursor | 类型修复、基础空状态、loading、error 状态 | `npm run build` 通过 | Codex |
| P1-M4-S6 | 更新 README、docs、`.env.example` | Codex | 启动说明、配置说明、Plan 1 设计文档 | 新读者能按文档启动项目 | Codex |
| P1-M4-S7 | 准备封版材料：截图、CHANGELOG、当前限制 | Cursor + Codex | `CHANGELOG.md`、截图文件、限制说明 | v0.1.0 功能边界清晰 | Codex |
| P1-M4-S8 | Plan 1 最终 review、修复、创建 tag | Codex + Claude Code | review 记录、修复 commit、`v0.1.0` tag | 全量测试通过，tag 存在 | Codex + Claude final review |

M4 完成后建议 commit：

```text
chore: release v0.1.0 foundation chat
```

---

## 7. 每次执行 1～3 步的标准流程

每次让 Codex / Cursor 执行时，建议按这个模板下发：

```text
当前执行范围：P1-Mx-Sy ～ P1-Mx-Sz
必须遵守：只做这些 Step，不提前做后续功能
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
2. 是否引入超出 Plan 1 的能力
3. 是否破坏已有启动流程
4. 是否有测试或手动验证证据
5. 是否同步 README / docs / env example
6. 是否留下未解释的临时代码或调试代码
7. 是否适合进入下一批次
```

---

## 8. Claude Code Review 节点

Claude Code 不需要每个 Step 都参与，建议在这些节点使用：

| 节点 | 审核重点 | 输入材料 |
|---|---|---|
| M2 结束 | Provider 抽象、配置结构、数据库模型是否稳定 | diff、目录结构、Provider 代码、测试结果 |
| M3 结束 | Chat / Streaming / 会话历史是否形成稳定闭环 | diff、API 设计、前端页面、测试结果 |
| M4 封版前 | v0.1.0 是否能作为 Plan 2 地基 | 全量 diff、README、测试结果、CHANGELOG |

Claude Code 审核后，Codex 负责：

```text
1. 判断哪些意见必须修
2. 拆成 1～3 个修复 Step
3. 修复后重新跑测试
4. 更新文档和 changelog
```

---

## 9. Plan 1 最终验收清单

| 验收项 | 状态 | 证据 |
|---|---|---|
| 后端能启动 | pending | 启动命令和输出 |
| 前端能启动 | pending | 启动命令和页面截图 |
| 前端能调用后端 health API | pending | 页面状态或接口响应 |
| 能配置 DeepSeek 或 OpenRouter API Key | pending | `.env.example` 和配置说明 |
| 能选择模型 | pending | 前端截图或接口响应 |
| 能发送消息 | pending | Chat 页面截图 |
| 能流式输出 | pending | SSE 验证或页面录屏 |
| 能保存会话 | pending | 数据库记录或接口响应 |
| 刷新页面后历史会话还在 | pending | 手动验证记录 |
| 能记录 provider / model / latency / token / cost | pending | `llm_calls` 记录 |
| API Key 错误时不会崩溃 | pending | 错误场景测试 |
| README 有启动说明 | pending | README 链接 |
| docs 有第一阶段设计文档 | pending | docs 链接 |
| 有 v0.1.0 tag | pending | `git tag --list` 输出 |

---

## 10. Plan 1 到 Plan 2 的桥接检查

只有下面 5 项都满足，才建议进入 Plan 2：

| 桥接项 | 状态 | 说明 |
|---|---|---|
| LLM Provider 的 `chat` 接口稳定 | pending | 后续可以扩展 `tools` 参数 |
| Message / Conversation 数据模型稳定 | pending | Agent Run 可以引用会话上下文 |
| Streaming Chat 不阻塞普通 Chat API | pending | 普通接口和 SSE 接口都可用 |
| 基础日志可定位 provider、model、latency 和错误原因 | pending | Plan 2 工具调用失败时可排查 |
| README 能让开发者从零启动前后端 | pending | Plan 2 不再反复修启动文档 |

---

## 11. 推荐文件位置

执行过程中建议把相关产物放在这些位置：

| 类型 | 路径 |
|---|---|
| 后端代码 | `backend/app/` |
| 后端测试 | `backend/tests/` |
| 前端代码 | `frontend/src/` |
| 前端测试或 smoke 检查 | `frontend/src/` 或 `frontend/tests/` |
| 计划源文档 | `docs-plan/` |
| 项目文档 | `docs/` |
| 本地草稿和敏感材料 | `docs-local/`（忽略，不提交） |
| 环境变量样例 | `.env.example`、`backend/.env.example`、`frontend/.env.example` |
| 版本记录 | `CHANGELOG.md` |
| 截图 | `docs/assets/plan1/` |

---

## 12. 执行建议

Plan 1 的重点不是做复杂功能，而是建立一个稳的底座。

推荐实际推进方式：

```text
每天只推进 1～2 个 Batch
每个 Batch 完成后马上 commit
每个 Milestone 完成后 Codex review
M2 已完成二审；下一次集中二审放在 M4 结束后
v0.1.0 tag 创建后再进入 Plan 2
```

只要 Plan 1 做稳，Plan 2 的 Tool Calling、Plan 3 的 RAG、Plan 5 的 Agent Runtime 都会轻很多。
