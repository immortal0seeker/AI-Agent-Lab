# Plan 6 执行步骤表｜Agent 工作台：MCP + Voice + Vision + Desktop

> 适用文档：`00-ALL PLAN/06-PLAN-6 (V1.0).md`  
> 执行方式：每次只领取连续 1～3 个 Step，完成后立即测试、提交、review。  
> 阶段目标：一个阶段完成一个里程碑；一个里程碑通过后再进入下一个里程碑。
> 外部复审策略覆盖（2026-07-18 用户决定）：不再使用 Claude Code；本文件后续所有 Claude Code / Claude review 节点均被此决定覆盖，不作为验收或推进门槛。每批只执行 Codex self-review；全部 6 个 Plan 和整个项目完成后，再由用户决定是否使用 Fable 5 做一次全项目检查。

---

## 0. 执行总原则

| 规则 | 说明 |
|---|---|
| 单次执行范围 | Cursor / Codex 每次只做 1～3 个连续 Step |
| 执行顺序 | 必须按 `P6-Mx-Sy` 顺序推进，除非 Codex 明确记录调整原因 |
| 每步完成定义 | 代码可运行、局部测试通过、相关文档或配置同步 |
| 每个阶段完成定义 | 阶段验收项全部通过，Codex review 后进入下一阶段 |
| Claude Code 使用时机 | MCP Client / Permission、Voice Pipeline、Vision Provider、Desktop Permission、封版前 |
| 提交节奏 | 每 1～3 个 Step 一次 commit；每个里程碑结束一次 review commit |
| 文档同步 | MCP transport、权限策略、Provider 配置、媒体存储、桌面权限、API 返回结构变化必须同步 docs 或 README |
| 敏感配置 | API key、token、MCP env secret 不明文入库、不写日志、不在 UI 明文展示；数据库只保存 secret reference 或本地加密配置引用 |
| 禁止提前做 | 多 Agent、A2A、Browser Use / Computer Use、插件市场、实时全双工语音、视频理解、移动端 App、企业多用户权限 |

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

## 1. Plan 6 总览

| 阶段 | 里程碑 | 对应原 PLAN6 Step | 核心交付 | 预计时间 | 主要工具 | 审核节点 |
|---|---|---|---|---:|---|---|
| Phase 1 | M1 交接与 MCP 数据 / Client 底座 | Step 1～6 | v0.5.0 交接检查、MCP Server / Tool 模型、Registry、stdio Client、Tool Discovery | 30～42 h | Codex | Codex + Claude Code |
| Phase 2 | M2 MCP Adapter / Permission / Runtime 接入 | Step 7～12 | MCP Tool Adapter、Permission Policy、Local Permission 基础、Tool Call Service、Runtime 接入、MCP API | 34～50 h | Codex | Codex + Claude Code |
| Phase 3 | M3 MCP 工具体系与管理页 | Step 12～17 | MCP 管理页、Filesystem / GitHub / SQLite MCP、Custom MCP Server、MCP 文档 | 34～50 h | Codex + Cursor | Codex + Claude Code |
| Phase 4 | M4 Voice 数据 / Provider / API | Step 18～22 | Audio 模型、Audio Storage、STT Provider、TTS Provider、Voice API | 28～40 h | Codex | Codex + Claude Code |
| Phase 5 | M5 Voice Pipeline / UI / Trace | Step 23～26 | 前端录音、Voice Pipeline、TTS 播放、Voice 页面、Audio Trace | 26～40 h | Codex + Cursor | Codex + Claude Code |
| Phase 6 | M6 Multimodal Media / OCR / Vision | Step 27～31 | Media Asset、上传、OCR Provider、Vision Provider、Multimodal API | 30～44 h | Codex | Codex + Claude Code |
| Phase 7 | M7 Image Chat / OCR to RAG / 多模态页面 | Step 32～34 | 图文问答、OCR 入库、多模态前端页面 | 24～36 h | Codex + Cursor | Codex + Claude Code |
| Phase 8 | M8 Desktop Shell / Config / Trusted Paths 接入 | Step 35～38 | Tauri 方案、桌面壳、本地配置、Trusted Paths UI 接入、Desktop Settings 页面 | 30～44 h | Codex + Cursor | Codex review |
| Phase 9 | M9 Desktop 权限 / 托盘 / 快捷键 / 打包 | Step 39～41 | 系统托盘、全局快捷键、本地文件权限、Windows 构建产物 | 22～34 h | Codex | Codex + Claude Code |
| Phase 10 | M10 测试、文档与 v0.6.0 封版 | Step 42～44 | 集成测试、docs、README、CHANGELOG、截图、v0.6.0 tag | 26～40 h | Codex + Cursor | Codex + Claude final review |

---

## 2. 执行节奏表

| 执行批次 | 建议领取范围 | 批次目标 | 完成后动作 | 状态 |
|---|---|---|---|---|
| Batch 1 | P6-M1-S1～P6-M1-S3 | 确认 Plan5 交接，建立 MCP 数据模型 | 迁移和模型测试 | 未完成 |
| Batch 2 | P6-M1-S4～P6-M1-S6 | 实现 Server Registry、stdio Client、Tool Discovery | MCP mock 连接测试 | 未完成 |
| Batch 3 | P6-M1-S7 | 完成 MCP Client 文档和 M1 review | Codex + Claude review M1 | 未完成 |
| Batch 4 | P6-M2-S1～P6-M2-S3 | 实现 Tool Adapter、Permission Policy、Tool Call Service | adapter / permission 测试 | 未完成 |
| Batch 5 | P6-M2-S4～P6-M2-S5 | 接入 Agent Runtime 和 Human Approval | Runtime 集成测试 | 未完成 |
| Batch 6 | P6-M2-S6～P6-M2-S8 | 实现 MCP API、Local Permission 基础与 M2 review | API / 权限测试，Claude review | 未完成 |
| Batch 7 | P6-M3-S1～P6-M3-S2 | 实现前端 MCP API 封装和管理页基础 | TypeScript 检查 + 页面手测 | 未完成 |
| Batch 8 | P6-M3-S3～P6-M3-S5 | 接入 Filesystem / GitHub / SQLite MCP 配置 | 工具发现测试 | 未完成 |
| Batch 9 | P6-M3-S6～P6-M3-S7 | 实现 Custom MCP Server 与 MCP 文档 | Codex + Claude review M3 | 未完成 |
| Batch 10 | P6-M4-S1～P6-M4-S3 | 建立 Audio 数据模型、Storage、STT Provider | 音频和转写 mock 测试 | 未完成 |
| Batch 11 | P6-M4-S4～P6-M4-S5 | 实现 TTS Provider 与 Voice API | API 测试 | 未完成 |
| Batch 12 | P6-M4-S6 | 完成 Voice Provider 文档和 M4 review | Codex + Claude review M4 | 未完成 |
| Batch 13 | P6-M5-S1～P6-M5-S2 | 实现前端录音和基础 VAD / 停止逻辑 | 浏览器手测 | 未完成 |
| Batch 14 | P6-M5-S3～P6-M5-S5 | 实现 Voice Pipeline、TTS 播放、Audio Trace | 端到端语音回合测试 | 未完成 |
| Batch 15 | P6-M5-S6 | 完成 Voice 页面和 M5 review | Codex + Claude review M5 | 未完成 |
| Batch 16 | P6-M6-S1～P6-M6-S2 | 建立 Media Asset 模型和上传服务 | 上传测试 | 未完成 |
| Batch 17 | P6-M6-S3～P6-M6-S4 | 实现 OCR Provider 和 Vision Provider | provider mock 测试 | 未完成 |
| Batch 18 | P6-M6-S5～P6-M6-S6 | 实现 Multimodal API 与 M6 review | API 测试，Claude review | 未完成 |
| Batch 19 | P6-M7-S1～P6-M7-S2 | 实现 Multimodal Prompt / 图文问答 | 图文问答 mock 测试 | 未完成 |
| Batch 20 | P6-M7-S3～P6-M7-S4 | 实现 OCR 入库和多模态页面 | 页面手测 | 未完成 |
| Batch 21 | P6-M7-S5 | 完成多模态文档和 M7 review | Codex + Claude review M7 | 未完成 |
| Batch 22 | P6-M8-S1～P6-M8-S2 | 完成桌面端方案并创建 Tauri 壳 | 本地启动测试 | 未完成 |
| Batch 23 | P6-M8-S3～P6-M8-S4 | 实现 Desktop API、本地配置并接入既有 Trusted Paths | API 测试 | 未完成 |
| Batch 24 | P6-M8-S5～P6-M8-S6 | 实现 Desktop Settings 页面和 M8 review | 页面手测，Codex review | 未完成 |
| Batch 25 | P6-M9-S1～P6-M9-S2 | 实现系统托盘、快捷键、本地权限校验 | 桌面手测 | 未完成 |
| Batch 26 | P6-M9-S3～P6-M9-S4 | 接入 Filesystem MCP 权限和 Windows 打包 | 权限测试 + 构建测试 | 未完成 |
| Batch 27 | P6-M9-S5 | 完成 Desktop 安全 review | Codex + Claude review M9 | 未完成 |
| Batch 28 | P6-M10-S1～P6-M10-S3 | 补齐 MCP / Voice / Multimodal / Desktop 测试 | 测试输出 | 未完成 |
| Batch 29 | P6-M10-S4～P6-M10-S5 | 更新 README、docs、CHANGELOG、截图 | 文档 review | 未完成 |
| Batch 30 | P6-M10-S6～P6-M10-S7 | 全量 review、修复、v0.6.0 封版 | Codex + Claude final review | 未完成 |

---

## 3. Phase 1｜M1 交接与 MCP 数据 / Client 底座

阶段目标：

```text
确认 Plan 5 的 Runtime、Tool Risk Policy、Human Approval、Trace、Context Engine 已可作为 MCP 底座，并建立 MCP Server 配置、连接、工具发现的基础能力。
```

阶段验收：

```text
1. Plan 5 到 Plan 6 的桥接项有明确证据
2. mcp_servers、mcp_tools、mcp_tool_calls、mcp_permissions 数据模型可用
3. MCP Server Registry 能保存、启停、更新连接状态
4. stdio MCP Client 可连接 mock server
5. Tool Discovery 能保存工具名称、描述、input_schema、risk_level、enabled 状态
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P6-M1-S1 | 检查 Plan 5 封版状态与桥接项 | Codex | Plan 5 交接检查记录 | Runtime、Approval、Trace、dynamic tool registration 有可运行证据 | Codex |
| P6-M1-S2 | 设计 MCP ORM 与迁移 | Codex | `mcp_servers`、`mcp_tools`、`mcp_tool_calls`、`mcp_permissions` 模型 | 迁移和模型测试通过 | Claude Code 可审 |
| P6-M1-S3 | 定义 MCP schema 与枚举 | Codex | `schemas/mcp.py`、`mcp_types.py` | transport_type、trust_level、tool status、risk_level 序列化测试通过 | Codex |
| P6-M1-S4 | 实现 MCP Server Registry | Codex | `server_registry.py` | create、update、list、disable、record_error 测试通过 | Codex |
| P6-M1-S5 | 实现 MCP stdio Client 与 Session | Codex | `mcp_client.py`、`mcp_session.py` | mock stdio server 可 initialize、list_tools、close | Claude Code 可审 |
| P6-M1-S6 | 实现 MCP Tool Discovery | Codex | `tool_discovery.py` | 发现工具后写入 mcp_tools，schema 保持原样 | Codex |
| P6-M1-S7 | 完成 MCP Client 文档和 M1 review | Codex | `docs/31-mcp-client.md` 初版 | 文档说明 transport、连接生命周期、当前只保证 stdio MVP | Codex + Claude review |

M1 完成后建议 commit：

```text
feat(mcp): add server registry client and discovery
```

---

## 4. Phase 2｜M2 MCP Adapter / Permission / Runtime 接入

阶段目标：

```text
把 MCP Tool 映射为 Runtime 可调度工具，并复用 Plan 5 的 Tool Risk Policy、Human Approval、Trace 和 Agent Run Detail。
```

阶段验收：

```text
1. MCP Tool Adapter 能把外部工具映射为 Runtime Tool
2. Permission Policy 能按 server trust、tool risk、path allowlist、network allowlist 判断是否允许调用
3. 高风险 MCP 调用会进入 Human Approval
4. MCP Tool Call 会写入 trace_step 和 mcp_tool_calls
5. Agent Runtime 可在 allowed_tools 内调用 MCP Tool
6. trusted_paths 基础模型、校验服务和 path_allowlist 判断已可被 Filesystem MCP 复用
7. MCP env、GitHub token、外部 Provider key 只保存 secret reference 或本地加密配置引用
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P6-M2-S1 | 实现 MCP Tool Adapter | Codex | `tool_adapter.py` | MCP tool schema 转 Runtime tool definition 测试通过 | Claude Code 可审 |
| P6-M2-S2 | 实现 MCP Permission Policy | Codex | `permission_policy.py` | trust_level、risk_level、path_allowlist、requires_approval 测试通过 | Claude Code 可审 |
| P6-M2-S3 | 实现 MCP Tool Call Service | Codex | `mcp_call_service.py` | 成功、失败、超时、权限拒绝均写入 call 记录 | Codex |
| P6-M2-S4 | 接入 Agent Runtime 工具注册 | Codex | Runtime dynamic tool registration hook | Agent Run 可看到启用的 MCP tools | Codex |
| P6-M2-S5 | 接入 Human Approval 与 Trace | Codex | approval + trace integration | 高风险 MCP call 创建 approval_request，Trace 可复盘 | Claude Code 可审 |
| P6-M2-S6 | 实现 MCP API | Codex | `api/v1/mcp.py` | server CRUD、connect、discover-tools、tool call、permission API 测试通过 | Codex |
| P6-M2-S7 | 前置实现 Local Permission 基础 | Codex | `desktop/trusted_paths.py`、`desktop/desktop_permissions.py` 基础版 | path normalize、trusted_paths、read/write/execute、path_allowlist 测试通过 | Claude Code 可审 |
| P6-M2-S8 | 完成 MCP Permission 文档和 M2 review | Codex | `docs/32-mcp-permissions.md` | 文档说明权限判断顺序、审批边界、secret 引用、失败行为 | Codex + Claude review |

M2 完成后建议 commit：

```text
feat(mcp): add tool adapter permissions and runtime integration
```

---

## 5. Phase 3｜M3 MCP 工具体系与管理页

阶段目标：

```text
提供可视化 MCP 管理页，并接入 Filesystem、GitHub、SQLite、自定义 MCP Server 的配置与发现流程。
```

阶段验收：

```text
1. 前端可配置 MCP Server、连接、发现工具、启停工具
2. Filesystem MCP 至少支持只读接入并受 trusted paths 约束
3. GitHub MCP 和 SQLite MCP 至少可保存配置、连接测试、发现工具
4. Custom MCP Server 可通过 command / args / env 配置
5. MCP 管理页能查看工具风险、权限和最近调用结果
6. token/env 等敏感值在 UI 中脱敏展示，后端日志和数据库不出现明文 secret
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P6-M3-S1 | 实现前端 MCP API 封装与类型 | Cursor | `frontend/src/api/mcp.ts`、`types/mcp.ts` | TypeScript 检查通过 | Codex |
| P6-M3-S2 | 实现 MCP 管理页面基础 | Cursor | `McpPage.tsx`、ServerList、ServerEditor、ToolTable | 页面可新增 server、连接、发现工具 | Codex |
| P6-M3-S3 | 接入 Filesystem MCP 配置 | Codex + Cursor | 文件系统 server 预设与只读策略 | 只读工具发现成功，越权路径被 Local Permission 基础拒绝 | Claude Code 可审 |
| P6-M3-S4 | 接入 GitHub MCP 配置 | Codex + Cursor | GitHub server 配置模板 | 只保存 token/env 的 secret reference，连接测试日志不含明文 token | Codex |
| P6-M3-S5 | 接入 SQLite MCP 配置 | Codex + Cursor | SQLite server 配置模板 | 可配置数据库路径，路径不可信时被拒绝 | Codex |
| P6-M3-S6 | 实现 Custom MCP Server 配置 | Codex | `custom_server.py` 与 UI 字段 | command、args、env secret reference、trust_level 可保存并 discover | Claude Code 可审 |
| P6-M3-S7 | 完成 MCP 工具体系文档和 M3 review | Codex | `docs/33-custom-mcp-server.md` | 文档说明 Filesystem / GitHub / SQLite / Custom 的配置方法与限制 | Codex + Claude review |

M3 完成后建议 commit：

```text
feat(mcp): add mcp management page and server presets
```

---

## 6. Phase 4｜M4 Voice 数据 / Provider / API

阶段目标：

```text
建立语音输入输出的后端底座：音频文件、STT、TTS、Voice Session、Voice Turn 和可替换 Provider 抽象。
```

阶段验收：

```text
1. audio_files、stt_transcripts、tts_outputs、voice_sessions、voice_turns 模型可用
2. Audio Storage 能保存录音和 TTS 输出
3. STT Provider 抽象和至少一个 mock / OpenAI-compatible provider 可用
4. TTS Provider 抽象和至少一个 mock / Edge / OpenAI-compatible provider 可用
5. Voice API 可上传音频、转写、合成、创建 session、查询 turn
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P6-M4-S1 | 设计 Audio / Voice ORM 与迁移 | Codex | `models/audio.py`、audio / voice tables | 迁移和模型测试通过 | Claude Code 可审 |
| P6-M4-S2 | 实现 Audio Storage | Codex | `audio_storage.py` | 保存、读取、删除音频文件记录测试通过 | Codex |
| P6-M4-S3 | 实现 STT Provider 抽象 | Codex | `providers/stt/base.py`、registry、mock/openai-compatible provider | mock 音频可返回 transcript | Claude Code 可审 |
| P6-M4-S4 | 实现 TTS Provider 抽象 | Codex | `providers/tts/base.py`、registry、mock/edge/openai-compatible provider | 文本可生成 tts_output 记录和音频文件 | Claude Code 可审 |
| P6-M4-S5 | 实现 Voice API | Codex | `api/v1/voice.py` | audio upload、transcribe、tts、session、turn API 测试通过 | Codex |
| P6-M4-S6 | 完成 STT / TTS Provider 文档和 M4 review | Codex | `docs/35-stt-tts-providers.md` | 文档说明 provider 配置、当前限制、测试方式 | Codex + Claude review |

M4 完成后建议 commit：

```text
feat(voice): add audio storage stt tts and voice api
```

---

## 7. Phase 5｜M5 Voice Pipeline / UI / Trace

阶段目标：

```text
把录音、STT、Agent Runtime、TTS、播放和 Trace 串成一个可用的 push-to-talk 语音回合。
```

阶段验收：

```text
1. 前端可录音、停止、上传音频
2. STT 转写文本可进入 Agent Runtime
3. Agent 文本回答可选 TTS 播放
4. voice_turn 能关联 conversation、agent_run、trace_run、audio、transcript、tts_output
5. Voice 页面能展示转写、回答、播放状态和 Trace 链接
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P6-M5-S1 | 实现前端 VoiceRecorder | Cursor | `VoiceRecorder.tsx` | 浏览器可录音、停止、生成 Blob、上传 | Codex |
| P6-M5-S2 | 实现基础 VAD / 手动停止策略 | Cursor + Codex | `vad.py` 或前端 silence detection | 手动停止可靠，VAD 可作为可选增强 | Codex |
| P6-M5-S3 | 实现 Voice Pipeline | Codex | `voice_pipeline.py` | audio -> STT -> Agent Runtime -> text answer -> optional TTS 测试通过 | Claude Code 可审 |
| P6-M5-S4 | 实现 TTS 播放组件 | Cursor | `TtsPlayer.tsx` | 前端可播放 tts_output 音频 | Codex |
| P6-M5-S5 | 接入 Voice Trace | Codex | `voice_trace.py` | Trace 中可看到 record、stt、agent_run、tts、latency | Claude Code 可审 |
| P6-M5-S6 | 实现 Voice 页面和 M5 review | Cursor + Codex | `VoicePage.tsx`、TranscriptPanel、VoiceTurnList | 可完成一次 push-to-talk 语音回合 | Codex + Claude review |

M5 完成后建议 commit：

```text
feat(voice): add push to talk voice agent pipeline
```

---

## 8. Phase 6｜M6 Multimodal Media / OCR / Vision

阶段目标：

```text
建立图片、截图和文档图像的媒体资产管理，并提供 OCR 与 VLM 分析 Provider。
```

阶段验收：

```text
1. media_assets、ocr_results、vision_analyses 模型可用
2. Media Service 能保存图片、计算 hash、记录宽高、mime_type、size
3. OCR Provider 可提取文本和 blocks
4. Vision Provider 可根据 prompt 分析图片
5. Multimodal API 可上传、查询、OCR、analyze
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P6-M6-S1 | 设计 Media / OCR / Vision ORM 与迁移 | Codex | `models/media.py`、media / ocr / vision tables | 迁移和模型测试通过 | Claude Code 可审 |
| P6-M6-S2 | 实现 Media Service 与上传 | Codex | `media_service.py` | 图片上传、hash、metadata、删除测试通过 | Codex |
| P6-M6-S3 | 实现 OCR Provider 抽象 | Codex | `providers/ocr/base.py`、registry、mock/local/api provider | mock 图片可返回 text、blocks、confidence | Claude Code 可审 |
| P6-M6-S4 | 实现 Vision Provider 抽象 | Codex | `providers/vision/base.py`、registry、mock/openai-compatible/qwen-vl provider | mock 图片 + prompt 可返回 result_text | Claude Code 可审 |
| P6-M6-S5 | 实现 Multimodal API 基础 | Codex | `api/v1/multimodal.py` | media upload/list/get/delete、ocr、analyze API 测试通过 | Codex |
| P6-M6-S6 | 完成 Vision / OCR 文档和 M6 review | Codex | `docs/36-multimodal-vision.md` | 文档说明 OCR、VLM、媒体存储、当前限制 | Codex + Claude review |

M6 完成后建议 commit：

```text
feat(multimodal): add media ocr and vision providers
```

---

## 9. Phase 7｜M7 Image Chat / OCR to RAG / 多模态页面

阶段目标：

```text
把图片和文本一起送入模型，支持截图分析、图文问答，并允许把 OCR 文本加入知识库。
```

阶段验收：

```text
1. Multimodal Prompt 支持单图、多图、OCR 文本、RAG sources
2. 图文问答能记录 vision trace_step
3. OCR 文本可转为 ParsedDocument 并复用 Plan 3 chunking / embedding
4. 前端可上传图片、OCR、VLM 分析、图文问答、OCR 入库
5. 图片相关 sources 可在回答和 Trace 中追踪
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P6-M7-S1 | 实现 Multimodal Prompt | Codex | `multimodal_prompt.py` | 单图、多图、OCR 辅助文本、RAG sources 组合测试通过 | Codex |
| P6-M7-S2 | 实现图文问答接口 | Codex | `POST /api/v1/multimodal/chat` | 图片 + 问题可返回 answer、sources、trace_run_id | Claude Code 可审 |
| P6-M7-S3 | 实现 OCR 结果入库 | Codex | `image_rag.py` | OCR text 可转 document、chunk、embedding，并带 source_media_id | Codex |
| P6-M7-S4 | 实现多模态前端页面 | Cursor | `MultimodalPage.tsx`、MediaUploadPanel、ImagePreview、OcrResultPanel、VisionAnalysisPanel | 浏览器可完成上传、OCR、分析、图文问答、入库 | Codex |
| P6-M7-S5 | 完成 OCR to RAG 文档和 M7 review | Codex | `docs/37-ocr-to-rag.md` | 文档说明 OCR 入库流程、metadata、限制和测试方法 | Codex + Claude review |

M7 完成后建议 commit：

```text
feat(multimodal): add image chat and ocr to rag
```

---

## 10. Phase 8｜M8 Desktop Shell / Config / Trusted Paths 接入

阶段目标：

```text
创建可运行的 Tauri 桌面壳，建立本地配置和 Desktop API，并把 M2 已前置的 Trusted Paths / Local Permission 能力接入桌面设置页面。
```

阶段验收：

```text
1. desktop/README.md 说明桌面端架构、启动方式、权限模型
2. Tauri 桌面壳可加载现有 React WebUI
3. desktop_settings 模型可用，trusted_paths 复用 M2 前置模型
4. Desktop API 可查询状态、配置、可信路径和路径校验结果
5. Desktop Settings 页面可管理可信路径、权限级别和本地连接状态
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P6-M8-S1 | 设计桌面端技术方案 | Codex | `desktop/README.md` | 方案说明 Tauri、React build、FastAPI 连接、本地权限边界 | Codex |
| P6-M8-S2 | 创建 Tauri 桌面壳 | Codex | `desktop/package.json`、`src-tauri/` | Windows 可打开桌面窗口并加载前端 | Codex |
| P6-M8-S3 | 设计 Desktop ORM 与迁移 | Codex | `models/desktop.py`、desktop_settings，复用 M2 trusted_paths | 迁移和模型测试通过，不重复创建 trusted_paths | Codex |
| P6-M8-S4 | 实现 Desktop API 与本地配置服务 | Codex | `desktop/local_config.py`、`api/v1/desktop.py`，接入 M2 `trusted_paths.py` | status、settings、trusted-paths、validate-path API 测试通过 | Codex |
| P6-M8-S5 | 实现 Desktop Settings 页面 | Cursor | `DesktopSettingsPage.tsx`、TrustedPathList、DesktopStatusPanel、LocalConfigEditor | 页面可管理可信路径和权限级别 | Codex |
| P6-M8-S6 | 完成 Desktop 设置 review | Codex + Cursor | 手测记录、截图、docs 更新 | Web 与 Desktop 使用同一套 trusted_paths 数据 | Codex review |

M8 完成后建议 commit：

```text
feat(desktop): add tauri shell local config and trusted paths ui
```

---

## 11. Phase 9｜M9 Desktop 权限 / 托盘 / 快捷键 / 打包

阶段目标：

```text
让桌面端具备日常使用形态，同时用 Trusted Paths 和 Human Approval 控制本地文件访问风险。
```

阶段验收：

```text
1. 系统托盘可显示、隐藏、恢复、退出应用
2. 全局快捷键可唤起窗口或打开语音输入
3. 本地路径访问必须经过 trusted_paths 校验
4. 写入和执行类本地操作需要 Human Approval
5. Windows 构建产物可启动 AI Agent Lab
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P6-M9-S1 | 实现系统托盘与全局快捷键 | Codex | `tray.rs`、`hotkeys.rs` | 可显示/隐藏窗口，默认快捷键可关闭或修改 | Codex |
| P6-M9-S2 | 强化 Desktop 本地文件权限校验 | Codex | `desktop_permissions.py` 增强版 | 桌面端 read/write/execute 权限、审批和 trusted_paths 边界测试通过 | Claude Code 可审 |
| P6-M9-S3 | 接入 Filesystem MCP 权限检查 | Codex | filesystem MCP pre-call guard | 越权路径拒绝并写入 trace_step | Claude Code 可审 |
| P6-M9-S4 | 打包 Windows 桌面端 | Codex | Tauri build 配置和构建产物 | Windows 构建可启动，版本号为 v0.6.0 | Codex |
| P6-M9-S5 | 完成 Desktop 权限文档和 M9 review | Codex | `docs/38-desktop-app.md`、`docs/39-local-permissions.md` | 文档说明 trusted_paths、审批、打包、当前限制 | Codex + Claude review |

M9 完成后建议 commit：

```text
feat(desktop): add tray hotkeys permissions and windows package
```

---

## 12. Phase 10｜M10 测试、文档与 v0.6.0 封版

阶段目标：

```text
补齐 MCP、Voice、Multimodal、Desktop 的测试、文档、截图、变更记录和封版检查，确保 v0.6.0 可以作为后续多 Agent 扩展的稳定工作台底座。
```

阶段验收：

```text
1. 核心集成逻辑不依赖真实 MCP Server、真实 STT/TTS/VLM 服务也能用 mock 跑通
2. MCP 管理页、Voice 页面、Multimodal 页面、Desktop Settings 页面有手测记录或截图
3. README、CHANGELOG、docs 覆盖 v0.6.0 能力、限制和启动方式
4. Plan 6 到后续多 Agent 扩展的桥接检查全部通过
5. v0.6.0 tag 创建前经过 Codex + Claude final review
```

| Step ID | 任务 | 建议工具 | 交付物 | 验证方式 | Review |
|---|---|---|---|---|---|
| P6-M10-S1 | 补齐 MCP 测试 | Codex | MCP registry/client/discovery/permission/adapter/call tests | mock MCP server 全流程测试通过 | Claude Code 可审 |
| P6-M10-S2 | 补齐 Voice 与 Multimodal 测试 | Codex | voice/media/ocr/vision/multimodal tests | mock STT/TTS/OCR/VLM 和图文问答测试通过 | Codex |
| P6-M10-S3 | 补齐 Desktop 与权限测试 | Codex | trusted paths、desktop API、permission guard tests | 越权路径、写入审批、桌面配置测试通过 | Claude Code 可审 |
| P6-M10-S4 | 补齐前端验证与截图 | Cursor + Codex | MCP、Voice、Multimodal、Desktop Settings、桌面窗口截图 | 浏览器和桌面手测记录齐全 | Codex |
| P6-M10-S5 | 更新 README、docs、CHANGELOG | Codex | v0.6.0 文档和版本记录 | 文档覆盖 MCP、Voice、Vision、Desktop、权限和限制 | Codex |
| P6-M10-S6 | 执行 Plan 6 全量 review 与修复 | Codex + Claude Code | review 记录、修复 commit | 全量测试通过，关键风险有处理结论 | Codex + Claude final review |
| P6-M10-S7 | 完成 v0.6.0 封版 | Codex | tag、截图、验收清单 | `git tag --list` 可见 v0.6.0，桥接项通过 | Codex |

M10 完成后建议 commit：

```text
chore: release v0.6.0 agent workspace
```

---

## 13. 每次执行 1～3 步的标准流程

每次让 Codex / Cursor 执行时，建议按这个模板下发：

```text
当前执行范围：P6-Mx-Sy ～ P6-Mx-Sz

必须遵守：
1. 只做这些 Step，不提前做多 Agent、A2A、Browser Use、Computer Use、插件市场、实时全双工语音或视频理解。
2. 保持 Plan 1～5 已有 Chat、Tool、RAG、Trace、Memory、Context Engine、Agent Runtime、Human Approval 能力兼容。
3. MCP、Voice、Vision、Desktop 都必须复用 Agent Runtime、Trace、Tool Risk Policy 和 Human Approval。
4. 任何数据库字段、状态枚举、Provider 配置、权限策略、API 返回结构变化都要同步测试和文档。
5. token、API key、MCP env secret 只能通过 secret reference 或本地加密配置传递，不能写入普通数据库字段、Trace、日志或前端状态快照。

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
2. 是否破坏 Plan 5 Runtime、Approval、Trace、Context Engine
3. MCP Tool 是否统一进入 Runtime Tool Registry
4. MCP Tool Call 是否经过 Permission Policy 和 Tool Risk Policy
5. 高风险 MCP、本地文件、外部 API 调用是否必须经过 Human Approval
6. Voice 输入是否最终转为 Agent Runtime 可处理的文本任务
7. TTS 输出是否只是表达层，不改变 Runtime 的事实记录
8. 图片 / OCR / VLM 结果是否有 media_id、trace、source 可追踪
9. OCR 入库是否复用 Plan 3 的文档解析、chunking、embedding 管线
10. Desktop Trusted Paths 是否同时约束内置文件工具和 Filesystem MCP
11. MCP env、GitHub token、Provider key 是否脱敏展示，且没有进入数据库明文字段、Trace 或日志
12. Trace 是否覆盖 MCP、STT、TTS、OCR、Vision、Desktop permission denied
13. README / docs / env example 是否同步
14. 是否适合进入下一批次
```

---

## 14. Claude Code Review 节点

Claude Code 不需要每个 Step 都参与，建议在这些节点使用：

| 节点 | 审核重点 | 输入材料 |
|---|---|---|
| M1 结束 | MCP Client、Session、Tool Discovery 是否能稳定支撑后续工具生态 | diff、ORM、schema、mock server、测试结果 |
| M2 结束 | MCP Adapter、Permission、Approval、Trace 是否存在绕过风险 | diff、permission policy、tool adapter、runtime hook、测试结果 |
| M3 结束 | Filesystem / GitHub / SQLite / Custom MCP 配置是否清晰可控，secret 是否无明文落库和日志 | diff、MCP 管理页、server templates、权限测试、secret 脱敏测试 |
| M4 结束 | STT / TTS Provider 抽象是否与既有 Provider 风格一致 | diff、provider registry、voice API、测试结果 |
| M5 结束 | Voice Pipeline 是否可靠记录 audio、transcript、agent_run、tts、trace | diff、voice_pipeline、VoicePage、Trace、手测记录 |
| M6 结束 | OCR / Vision Provider 是否可替换，媒体文件和结果是否可审计 | diff、media service、ocr / vision providers、测试结果 |
| M7 结束 | OCR 入库是否复用 RAG 管线，图文问答是否避免伪造图片内容 | diff、multimodal prompt、image_rag、页面手测 |
| M9 结束 | Desktop 本地权限是否足够保守，Trusted Paths 是否无法绕过 | diff、desktop permissions、filesystem guard、桌面手测 |
| M10 封版前 | v0.6.0 是否能作为后续多 Agent / A2A / Browser Use 的工作台底座 | 全量 diff、README、测试结果、截图、CHANGELOG、桥接检查 |

Claude Code 审核后，Codex 负责：

```text
1. 判断哪些意见必须修
2. 拆成 1～3 个修复 Step
3. 修复后重新跑测试
4. 更新文档和 changelog
5. 记录是否允许进入下一阶段
```

---

## 15. Plan 6 最终验收清单

| 验收项 | 状态 | 证据 |
|---|---|---|
| mcp_servers 表可用 | pending | ORM / migration / test |
| mcp_tools 表可用 | pending | ORM / migration / test |
| mcp_tool_calls 表可用 | pending | tool call test |
| mcp_permissions 表可用 | pending | permission test |
| MCP Server Registry 可用 | pending | registry test |
| MCP stdio Client 可用 | pending | mock server test |
| MCP Tool Discovery 可用 | pending | discovery test |
| MCP Tool Adapter 可用 | pending | adapter test |
| MCP Permission Policy 可用 | pending | permission test |
| MCP Tool Call Service 可用 | pending | call service test |
| MCP API 可用 | pending | API test |
| MCP 管理页面可用 | pending | 页面截图 |
| Filesystem MCP 可用 | pending | read-only tool test |
| GitHub MCP 可配置 | pending | config test |
| SQLite MCP 可配置 | pending | config test |
| Custom MCP Server 可用 | pending | custom server test |
| audio_files 表可用 | pending | ORM / migration / test |
| STT Provider 抽象完成 | pending | provider test |
| 至少一个 STT Provider 可用 | pending | STT mock or real test |
| TTS Provider 抽象完成 | pending | provider test |
| 至少一个 TTS Provider 可用 | pending | TTS mock or real test |
| Voice API 可用 | pending | API test |
| Voice Pipeline 可用 | pending | voice turn test |
| 前端录音可用 | pending | 页面截图 |
| TTS 播放可用 | pending | 页面截图 |
| 基础 VAD 或手动停止可用 | pending | browser test |
| media_assets 表可用 | pending | ORM / migration / test |
| OCR Provider 抽象完成 | pending | provider test |
| 至少一个 OCR Provider 可用 | pending | OCR mock or real test |
| Vision Provider 抽象完成 | pending | provider test |
| 至少一个 Vision Provider 可用 | pending | Vision mock or real test |
| Multimodal API 可用 | pending | API test |
| 图文问答可用 | pending | multimodal chat test |
| OCR 结果可加入知识库 | pending | image_rag test |
| Multimodal 页面可用 | pending | 页面截图 |
| Tauri 桌面端可启动 | pending | desktop screenshot |
| Desktop API 可用 | pending | API test |
| trusted_paths 可用 | pending | permission test |
| Desktop Settings 页面可用 | pending | 页面截图 |
| 系统托盘可用 | pending | 桌面手测 |
| 全局快捷键可用 | pending | 桌面手测 |
| 本地文件权限检查可用 | pending | permission denied test |
| 核心测试已补齐 | pending | test output |
| README 已更新 | pending | README link |
| docs 已更新 | pending | docs links |
| CHANGELOG 已更新 | pending | changelog link |
| 已创建 v0.6.0 tag | pending | `git tag --list` 输出 |

---

## 16. Plan 6 到后续多 Agent 扩展的桥接检查

只有下面 6 项都满足，才建议进入后续多 Agent / A2A / Browser Use 扩展：

| 桥接项 | 状态 | 说明 |
|---|---|---|
| MCP Tool Adapter 能把外部工具统一映射为 Runtime Tool | pending | 后续多 Agent 可共享同一工具生态 |
| Human Approval 覆盖 Filesystem MCP、本地文件访问和付费 API 调用 | pending | 高风险动作不会因入口不同而绕过审批 |
| Trace Timeline 能展示文本、语音、图片、MCP Tool Call 的统一执行过程 | pending | 多 Agent 协作前先保证单 Agent 可复盘 |
| Desktop Trusted Paths 和 Web 工具权限边界使用同一套策略 | pending | 本地权限不因桌面端入口而放宽 |
| Voice / Vision 输入最终都转成 Agent Runtime 可处理的任务上下文 | pending | 后续 Agent Handoff 不需要重新设计输入管线 |
| MCP、Voice、Vision、Desktop 都有 mock 测试闭环 | pending | 后续扩展不会被外部服务稳定性拖住 |

---

## 17. 推荐文件位置

执行过程中建议把相关产物放在这些位置：

| 类型 | 路径 |
|---|---|
| MCP 类型与服务 | `backend/app/mcp/` |
| MCP ORM | `backend/app/models/mcp.py` |
| MCP schema | `backend/app/schemas/mcp.py` |
| MCP API | `backend/app/api/v1/mcp.py` |
| Voice 类型与服务 | `backend/app/voice/` |
| Audio ORM | `backend/app/models/audio.py` |
| Audio schema | `backend/app/schemas/audio.py` |
| Voice API | `backend/app/api/v1/voice.py` |
| STT Provider | `backend/app/providers/stt/` |
| TTS Provider | `backend/app/providers/tts/` |
| Multimodal 服务 | `backend/app/multimodal/` |
| Media ORM | `backend/app/models/media.py` |
| Media schema | `backend/app/schemas/media.py` |
| Multimodal API | `backend/app/api/v1/multimodal.py` |
| OCR Provider | `backend/app/providers/ocr/` |
| Vision Provider | `backend/app/providers/vision/` |
| Desktop 后端服务 | `backend/app/desktop/` |
| Local Permission 基础 | `backend/app/desktop/trusted_paths.py`、`backend/app/desktop/desktop_permissions.py` |
| Desktop ORM | `backend/app/models/desktop.py` |
| Desktop API | `backend/app/api/v1/desktop.py` |
| MCP 前端 | `frontend/src/pages/McpPage.tsx`、`frontend/src/components/mcp/` |
| Voice 前端 | `frontend/src/pages/VoicePage.tsx`、`frontend/src/components/voice/` |
| Multimodal 前端 | `frontend/src/pages/MultimodalPage.tsx`、`frontend/src/components/multimodal/` |
| Desktop Settings 前端 | `frontend/src/pages/DesktopSettingsPage.tsx`、`frontend/src/components/desktop/` |
| 前端 API 封装 | `frontend/src/api/mcp.ts`、`frontend/src/api/voice.ts`、`frontend/src/api/multimodal.ts`、`frontend/src/api/desktop.ts` |
| 桌面端 | `desktop/`、`desktop/src-tauri/` |
| 后端测试 | `backend/tests/mcp/`、`backend/tests/voice/`、`backend/tests/multimodal/`、`backend/tests/desktop/` |
| 前端验证记录 | `docs/assets/plan6/` |
| 项目文档 | `docs/30-plan-6-agent-workspace.md`、`docs/31-mcp-client.md`、`docs/32-mcp-permissions.md`、`docs/33-custom-mcp-server.md`、`docs/34-voice-agent.md`、`docs/35-stt-tts-providers.md`、`docs/36-multimodal-vision.md`、`docs/37-ocr-to-rag.md`、`docs/38-desktop-app.md`、`docs/39-local-permissions.md` |

---

## 18. 执行建议

Plan 6 是项目从“Web 上的 Agent Runtime”走向“可日常使用的 AI Engineering Workspace”的阶段。推进时不要把 MCP、Voice、Vision、Desktop 做成四个互不相干的 Demo，而要让它们都复用同一个 Runtime 底座：

```text
MCP 工具由 Agent Runtime 调度
语音转文字后进入 Agent Runtime
图片分析结果进入 Agent Runtime 上下文
桌面端只是 Runtime 的本地使用形态
Human Approval 统一保护高风险动作
Trace 统一复盘所有入口的执行过程
```

推荐实际推进方式：

```text
先做 MCP 数据、连接、发现、权限和 Runtime 接入
再做 MCP 管理页和常用 MCP Server 配置
再做语音输入输出闭环
再做图片 / OCR / VLM 闭环
再做桌面壳、本地配置和 trusted paths
最后补测试、文档、截图和 v0.6.0 封版
```

如果时间紧，优先保住：

```text
MCP stdio Client
MCP Tool Discovery
MCP Tool Adapter
MCP Permission Policy
MCP Runtime 接入
STT Provider
TTS Provider
Voice Pipeline
Media Upload
OCR Provider
Vision Provider
Multimodal API
Tauri 桌面壳
Trusted Paths
README 和核心测试
```

GitHub MCP、SQLite MCP、Custom MCP Server 的高级体验、复杂 VAD、流式 TTS、系统托盘、全局快捷键和 Windows 安装包优化都可以在 v0.6.x 继续增强；但 MCP 权限边界、语音闭环、图片分析闭环和本地可信路径不能省略，否则后续多 Agent、Browser Use、Computer Use 都会缺少稳定而保守的安全基础。
