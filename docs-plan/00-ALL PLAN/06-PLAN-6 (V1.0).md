# Plan 6｜Agent 工作台：MCP + Voice + Vision + Desktop

## 0. 子计划定位

Plan 6 对应项目总路线中的：

```text
Plan 6：Agent 工作台
对应阶段口径：Phase 7 MCP + 工程扩展 + Phase 8 语音 / 多模态 / 桌面端
```

Plan 6 的前置条件是：

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

Plan 5 已完成
版本：v0.5.0
成果：Memory + Context Engine + Agent Runtime + Human Approval 可运行
```

也就是说，项目已经具备：

- FastAPI 后端

- React WebUI

- LLM Provider 抽象

- Streaming Chat

- Tool Registry

- Knowledge Base

- Naive RAG

- Advanced RAG

- RAG Evaluation

- Trace Timeline

- Memory

- Context Engine

- Agent Runtime 状态机

- ReAct Agent

- Planner-Executor

- Human Approval

- Retry / Error Recovery

- Checkpoint / Resume

- Agent Run 页面

Plan 6 不重写 Agent Runtime。

Plan 6 的目标是在 Plan 5 的 Runtime 底座上扩展产品形态和外部能力：

> MCP 工具生态、语音输入输出、多模态图片理解、OCR、桌面端、本地权限和本地工作台体验。

Plan 6 的重点是让 AI Agent Lab 从“Web 上的 Agent Runtime”升级为：

> 可以连接外部工具、理解语音和图片、读取本地资源、作为桌面应用日常使用的 AI Engineering Workspace。

---

## 1. Plan 6 核心目标

Plan 6 的核心目标是：

> 把 Agent Runtime 接入更大的工具生态和更自然的交互方式，让用户可以通过 Web 或桌面端使用 Agent 完成真实工程工作。

完成 Plan 6 后，系统应该支持：

```text
用户在桌面端打开 AI Agent Lab
    -> 系统加载本地配置和可信路径
    -> 用户配置 MCP Server
    -> 系统发现 MCP Tools
    -> Runtime 将 MCP Tools 注册为可调用工具
    -> Agent 根据任务选择内置工具或 MCP 工具
    -> 高风险 MCP Tool Call 进入 Human Approval
    -> Tool Call、Trace、Cost、错误统一记录
```

同时支持：

```text
用户点击麦克风
    -> 录音
    -> VAD 或手动停止
    -> STT 转写
    -> 转写文本进入 Agent Runtime
    -> Agent 返回文本
    -> 可选 TTS 播放
    -> Voice Turn 写入 Trace 和 Conversation
```

同时支持：

```text
用户上传截图或图片
    -> 系统保存 media asset
    -> 可选 OCR
    -> 可选 VLM 分析
    -> OCR 结果可进入 RAG
    -> 图片和文本一起进入 Multimodal Chat
    -> Agent 可以基于截图、图表、UI、文档图片回答问题
```

典型验收场景：

```text
用户在 Windows 桌面端打开应用。

用户说：
帮我看一下这个项目文件夹，并总结 README、数据库结构和最近的待办事项。

系统应该可以：
1. 通过桌面端读取可信本地目录
2. 通过 Filesystem MCP 或内置文件工具列出文件
3. 通过 Agent Runtime 规划任务
4. 在读取本地文件前检查路径权限
5. 执行 MCP Tool Call
6. 在 Trace 中展示每一步
7. 用户可以用语音继续追问
8. 用户可以上传截图，让 Agent 解释截图中的报错或 UI
9. 最终生成一份工程分析报告
```

Plan 6 的成果不是单个功能，而是：

> 一个具备外部工具生态、语音入口、多模态输入和桌面壳的 AI Agent 工程工作台。

---

## 2. Plan 6 不做什么

为了控制范围，Plan 6 暂时不做：

| 暂不做 | 原因 |
| --- | --- |
| 多 Agent 协作 | 放到 Phase 9 或后续 Plan，Plan 6 只增强单 Agent 工作台 |
| A2A / Agent-to-Agent 协议 | 依赖多 Agent 设计，后置 |
| 插件市场 | MCP 接入先做本地配置和可信 Server，不做市场分发 |
| Browser Use / Computer Use 完整自动化 | 风险高，依赖更强权限与沙箱，后置 |
| 端到端实时语音对话 | Plan 6 先做 push-to-talk 和基础 TTS，不做全双工打断 |
| 高级说话人分离 | 可研究，但不进入 v0.6.0 必需范围 |
| 视频理解 | 后置到多模态扩展，不进本阶段 MVP |
| 完整文档版面还原 | Plan 6 只做 OCR 和基础图片/文档图像理解 |
| 手机端 App | 本阶段只做 Web + Desktop |
| 企业级多用户权限 | 保持单用户学习项目边界 |
| 复杂本地沙箱 | 先做可信路径、工具白名单、审批和日志 |
| 本地模型管理平台 | 可以接 Ollama / 本地 Provider，但不做模型下载和管理中心 |

Plan 6 只做：

> MCP + Voice + Vision + Desktop 的可运行闭环。

---

## 3. Plan 6 版本目标

| 项目 | 内容 |
| --- | --- |
| 子计划名称 | Plan 6：Agent 工作台 |
| 对应范围 | MCP + 语音 + 多模态 + 桌面端 |
| 对应 Phase | Phase 7 + Phase 8 |
| 起始版本 | v0.5.0 |
| 目标版本 | v0.6.0 |
| 核心能力 | 外部工具生态、语音交互、图片理解、桌面工作台 |
| 预计时间 | 180～300 小时 |
| 难度 | 高 |
| 项目价值 | 把 Agent Runtime 产品化为可日常使用的 AI Engineering Workspace |

---

## 4. Plan 6 技术重点

Plan 6 重点学习和实现：

- MCP Client

- MCP Server Registry

- MCP Tool Discovery

- MCP Tool Adapter

- MCP Tool Permission

- Filesystem MCP

- GitHub MCP

- SQLite MCP

- Custom MCP Server

- MCP Server Trust Level

- STT Provider

- TTS Provider

- Audio Recording

- VAD

- Push-to-talk

- Voice Agent Pipeline

- Audio Trace

- OCR Provider

- Vision / VLM Provider

- Image Upload

- Screenshot Analysis

- Image + Text Chat

- OCR to RAG

- Multimodal Message

- Tauri Desktop App

- Local Config

- Trusted Local Paths

- Desktop Hotkey

- System Tray

- Local Backend Launch

- Packaging

- Desktop Permission Boundary

---

## 5. Plan 6 推荐里程碑拆分

| 里程碑 | 名称 | 内容 | 预计时间 |
| --- | --- | --- | --- |
| M1 | MCP 基础设施 | MCP Server 配置、连接、工具发现、Tool Adapter、权限策略 | 35～55 h |
| M2 | MCP 工具生态 | Filesystem / GitHub / SQLite MCP 接入、自定义 MCP Server、前端管理页 | 35～60 h |
| M3 | 语音系统 | STT Provider、录音、转写、TTS Provider、Voice Pipeline、语音 UI | 35～55 h |
| M4 | 多模态系统 | Media Asset、OCR、VLM、图片问答、OCR 入库、截图分析 | 35～60 h |
| M5 | 桌面端 | Tauri 壳、本地配置、可信路径、热键、托盘、打包发布 | 35～55 h |
| M6 | 测试与封版 | MCP / Audio / Vision / Desktop 测试、文档、截图、v0.6.0 | 25～40 h |

Plan 6 的风险点是横跨太多领域。

推荐优先级：

```text
必须完成：
MCP Client、MCP Tool Discovery、MCP Tool Adapter、MCP Permission、STT、TTS、图片上传、OCR、VLM Provider、桌面端可启动

尽量完成：
Filesystem MCP、GitHub MCP、SQLite MCP、自定义 MCP Server、OCR 入库、截图分析、系统托盘、快捷键

可以延期：
流式语音对话、语音打断、视频理解、Browser MCP、复杂本地沙箱、插件市场、移动端
```

---

## 6. Plan 6 推荐目录结构调整

在 Plan 5 基础上，后端新增：

```text
backend/app/
├── mcp/
│   ├── mcp_types.py
│   ├── mcp_client.py
│   ├── mcp_session.py
│   ├── server_registry.py
│   ├── tool_discovery.py
│   ├── tool_adapter.py
│   ├── permission_policy.py
│   ├── mcp_call_service.py
│   └── custom_server.py
├── voice/
│   ├── audio_types.py
│   ├── audio_storage.py
│   ├── stt_service.py
│   ├── tts_service.py
│   ├── vad.py
│   ├── voice_pipeline.py
│   └── voice_trace.py
├── multimodal/
│   ├── media_types.py
│   ├── media_service.py
│   ├── ocr_service.py
│   ├── vision_service.py
│   ├── multimodal_prompt.py
│   ├── image_rag.py
│   └── screenshot_analysis.py
├── desktop/
│   ├── local_config.py
│   ├── trusted_paths.py
│   ├── desktop_permissions.py
│   └── desktop_status.py
├── providers/
│   ├── stt/
│   │   ├── base.py
│   │   ├── openai_compatible.py
│   │   ├── local_whisper.py
│   │   └── registry.py
│   ├── tts/
│   │   ├── base.py
│   │   ├── edge_tts_provider.py
│   │   ├── openai_compatible.py
│   │   └── registry.py
│   ├── vision/
│   │   ├── base.py
│   │   ├── openai_compatible.py
│   │   ├── qwen_vl.py
│   │   └── registry.py
│   └── ocr/
│       ├── base.py
│       ├── local_ocr.py
│       ├── api_ocr.py
│       └── registry.py
├── models/
│   ├── mcp.py
│   ├── audio.py
│   ├── media.py
│   └── desktop.py
├── schemas/
│   ├── mcp.py
│   ├── audio.py
│   ├── media.py
│   └── desktop.py
└── api/v1/
    ├── mcp.py
    ├── voice.py
    ├── multimodal.py
    └── desktop.py
```

前端新增：

```text
frontend/src/
├── pages/
│   ├── McpPage.tsx
│   ├── VoicePage.tsx
│   ├── MultimodalPage.tsx
│   └── DesktopSettingsPage.tsx
├── components/
│   ├── mcp/
│   │   ├── McpServerList.tsx
│   │   ├── McpServerEditor.tsx
│   │   ├── McpToolTable.tsx
│   │   ├── McpPermissionPanel.tsx
│   │   └── McpToolCallPreview.tsx
│   ├── voice/
│   │   ├── VoiceRecorder.tsx
│   │   ├── TranscriptPanel.tsx
│   │   ├── TtsPlayer.tsx
│   │   ├── VoiceTurnList.tsx
│   │   └── AudioProviderSettings.tsx
│   ├── multimodal/
│   │   ├── MediaUploadPanel.tsx
│   │   ├── ImagePreview.tsx
│   │   ├── OcrResultPanel.tsx
│   │   ├── VisionAnalysisPanel.tsx
│   │   └── MultimodalSourceCard.tsx
│   └── desktop/
│       ├── TrustedPathList.tsx
│       ├── HotkeySettings.tsx
│       ├── DesktopStatusPanel.tsx
│       └── LocalConfigEditor.tsx
├── api/
│   ├── mcp.ts
│   ├── voice.ts
│   ├── multimodal.ts
│   └── desktop.ts
└── types/
    ├── mcp.ts
    ├── voice.ts
    ├── media.ts
    └── desktop.ts
```

桌面端新增：

```text
desktop/
├── package.json
├── src-tauri/
│   ├── tauri.conf.json
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs
│       ├── commands.rs
│       ├── tray.rs
│       ├── hotkeys.rs
│       └── permissions.rs
└── README.md
```

说明：

```text
Plan 6 推荐先用 Tauri。
原因是它更轻量，适合 Windows 本地工具、系统托盘、快捷键和本地文件权限。
如果后续发现 Tauri 对某些 Node 生态依赖不友好，再评估 Electron。
```

---

## 7. Plan 6 数据库设计

### 7.1 mcp_servers

用于保存 MCP Server 配置。

```sql
mcp_servers
- id
- name
- description
- transport_type
- command
- args_json
- env_json
- url
- trust_level
- status
- last_connected_at
- last_error
- created_at
- updated_at
```

`transport_type` 建议：

```text
stdio
sse
http
```

`trust_level` 建议：

```text
trusted
restricted
untrusted
disabled
```

---

### 7.2 mcp_tools

用于保存发现到的 MCP Tool。

```sql
mcp_tools
- id
- mcp_server_id
- name
- title
- description
- input_schema_json
- output_schema_json
- risk_level
- enabled
- discovered_at
- updated_at
```

---

### 7.3 mcp_tool_calls

用于记录 MCP Tool Call。

```sql
mcp_tool_calls
- id
- agent_run_id
- trace_step_id
- mcp_server_id
- mcp_tool_id
- tool_name
- input_json
- output_json
- status
- latency_ms
- error_message
- approval_request_id
- created_at
```

说明：

```text
如果 Plan 2/5 已有统一 tool_calls 表，可以把 mcp_tool_calls 作为扩展表。
不要重复记录；至少要能从 tool_call 追到 mcp_server 和 trace_step。
```

---

### 7.4 mcp_permissions

用于保存 MCP 工具权限。

```sql
mcp_permissions
- id
- mcp_server_id
- mcp_tool_id
- permission_scope
- allow
- requires_approval
- path_allowlist_json
- network_allowlist_json
- created_at
- updated_at
```

---

### 7.5 audio_files

用于保存录音和 TTS 音频文件记录。

```sql
audio_files
- id
- file_type
- file_path
- mime_type
- duration_ms
- sample_rate
- size_bytes
- source
- created_at
```

`file_type` 建议：

```text
recording
tts_output
imported_audio
```

---

### 7.6 stt_transcripts

用于保存语音转写结果。

```sql
stt_transcripts
- id
- audio_file_id
- provider
- model
- language
- text
- segments_json
- confidence
- latency_ms
- created_at
```

---

### 7.7 tts_outputs

用于保存语音合成结果。

```sql
tts_outputs
- id
- text
- provider
- model
- voice
- speed
- audio_file_id
- latency_ms
- created_at
```

---

### 7.8 voice_sessions

用于记录一次语音交互会话。

```sql
voice_sessions
- id
- conversation_id
- status
- started_at
- ended_at
- created_at
```

---

### 7.9 voice_turns

用于记录每一轮语音交互。

```sql
voice_turns
- id
- voice_session_id
- conversation_id
- agent_run_id
- trace_run_id
- input_audio_file_id
- transcript_id
- user_text
- assistant_text
- tts_output_id
- status
- created_at
```

---

### 7.10 media_assets

用于保存图片、截图、文档图像等媒体资源。

```sql
media_assets
- id
- media_type
- file_path
- original_filename
- mime_type
- width
- height
- size_bytes
- hash
- source
- metadata_json
- created_at
```

`media_type` 建议：

```text
image
screenshot
pdf_page_image
diagram
chart
```

---

### 7.11 ocr_results

用于保存 OCR 结果。

```sql
ocr_results
- id
- media_asset_id
- provider
- model
- text
- blocks_json
- confidence
- latency_ms
- created_at
```

---

### 7.12 vision_analyses

用于保存 VLM 分析结果。

```sql
vision_analyses
- id
- media_asset_id
- provider
- model
- prompt
- result_text
- structured_json
- latency_ms
- created_at
```

---

### 7.13 desktop_settings

用于保存桌面端配置。

```sql
desktop_settings
- id
- key
- value_json
- updated_at
```

---

### 7.14 trusted_paths

用于保存桌面端可信本地路径。

```sql
trusted_paths
- id
- path
- permission_level
- description
- enabled
- created_at
- updated_at
```

`permission_level` 建议：

```text
read
write
execute
```

---

## 8. Plan 6 核心接口设计

### 8.1 MCP API

```text
POST /api/v1/mcp/servers
GET /api/v1/mcp/servers
GET /api/v1/mcp/servers/{server_id}
PUT /api/v1/mcp/servers/{server_id}
DELETE /api/v1/mcp/servers/{server_id}

POST /api/v1/mcp/servers/{server_id}/connect
POST /api/v1/mcp/servers/{server_id}/disconnect
POST /api/v1/mcp/servers/{server_id}/discover-tools
GET /api/v1/mcp/servers/{server_id}/tools
PUT /api/v1/mcp/tools/{tool_id}
POST /api/v1/mcp/tools/{tool_id}/call

GET /api/v1/mcp/permissions
PUT /api/v1/mcp/permissions/{permission_id}
```

用途：

```text
让前端可以配置 MCP Server、发现工具、启停工具、测试工具调用和配置权限。
```

---

### 8.2 Voice API

```text
POST /api/v1/voice/audio-files
POST /api/v1/voice/transcribe
POST /api/v1/voice/tts
POST /api/v1/voice/sessions
GET /api/v1/voice/sessions
GET /api/v1/voice/sessions/{session_id}
POST /api/v1/voice/turns
GET /api/v1/voice/turns/{turn_id}
GET /api/v1/voice/providers
```

用途：

```text
支持录音上传、STT、TTS、语音回合记录和 Provider 配置。
```

---

### 8.3 Multimodal API

```text
POST /api/v1/multimodal/media
GET /api/v1/multimodal/media
GET /api/v1/multimodal/media/{media_id}
DELETE /api/v1/multimodal/media/{media_id}

POST /api/v1/multimodal/media/{media_id}/ocr
POST /api/v1/multimodal/media/{media_id}/analyze
POST /api/v1/multimodal/chat
POST /api/v1/multimodal/media/{media_id}/add-to-knowledge-base
```

用途：

```text
支持图片上传、OCR、VLM 分析、图文问答和 OCR 结果入库。
```

---

### 8.4 Desktop API

```text
GET /api/v1/desktop/status
GET /api/v1/desktop/settings
PUT /api/v1/desktop/settings/{key}
GET /api/v1/desktop/trusted-paths
POST /api/v1/desktop/trusted-paths
PUT /api/v1/desktop/trusted-paths/{path_id}
DELETE /api/v1/desktop/trusted-paths/{path_id}
POST /api/v1/desktop/validate-path
```

用途：

```text
让 Web 后端和桌面壳共享本地配置、可信路径和权限状态。
```

---

### 8.5 Provider API 扩展

```text
GET /api/v1/providers/stt
GET /api/v1/providers/tts
GET /api/v1/providers/vision
GET /api/v1/providers/ocr
POST /api/v1/providers/test
```

用途：

```text
把 Plan 1 的 Provider 抽象扩展到语音、视觉和 OCR。
```

---

## 9. Plan 6 核心数据结构

### 9.1 McpServerConfig

```python
class McpServerConfig:
    id: str
    name: str
    transport_type: str
    command: str | None
    args: list[str]
    env: dict
    url: str | None
    trust_level: str
    enabled: bool
```

---

### 9.2 McpTool

```python
class McpTool:
    id: str
    server_id: str
    name: str
    description: str
    input_schema: dict
    risk_level: str
    enabled: bool
```

---

### 9.3 McpToolCallRequest

```python
class McpToolCallRequest:
    server_id: str
    tool_name: str
    arguments: dict
    agent_run_id: str | None
    trace_run_id: str | None
```

---

### 9.4 STTResult

```python
class STTResult:
    text: str
    language: str | None
    segments: list[dict]
    confidence: float | None
    duration_ms: int | None
```

---

### 9.5 TTSResult

```python
class TTSResult:
    audio_file_id: str
    mime_type: str
    duration_ms: int | None
    provider: str
    model: str
```

---

### 9.6 VoiceTurn

```python
class VoiceTurn:
    id: str
    conversation_id: str
    transcript_text: str
    assistant_text: str | None
    tts_audio_file_id: str | None
    trace_run_id: str | None
```

---

### 9.7 MediaAsset

```python
class MediaAsset:
    id: str
    media_type: str
    file_path: str
    mime_type: str
    width: int | None
    height: int | None
    metadata: dict
```

---

### 9.8 OCRResult

```python
class OCRResult:
    media_asset_id: str
    text: str
    blocks: list[dict]
    confidence: float | None
```

---

### 9.9 VisionAnalysis

```python
class VisionAnalysis:
    media_asset_id: str
    prompt: str
    result_text: str
    structured: dict
    provider: str
    model: str
```

---

### 9.10 TrustedPath

```python
class TrustedPath:
    id: str
    path: str
    permission_level: str
    enabled: bool
```

---

## 10. Plan 6 详细步骤

## Step 1：确认 Plan 5 封版状态

### 要做什么

检查 v0.5.0 是否稳定。

### 检查清单

```text
[ ] Memory 可用
[ ] Context Engine 可用
[ ] Agent Runtime 状态机可用
[ ] ReAct Agent 可用
[ ] Planner-Executor 可用
[ ] Human Approval 可用
[ ] Tool Risk Policy 可用
[ ] Retry / Error Recovery 可用
[ ] Checkpoint / Resume 可用
[ ] Agent Run 页面可用
[ ] Trace Timeline 可用
[ ] 已创建 tag v0.5.0
```

### 完成标准

```text
Plan 6 不重写 Runtime，只把 MCP、Voice、Vision、Desktop 接入 Runtime。
```

### 预计时间

2～4 小时

---

## Step 2：设计 MCP 数据模型

### 要做什么

创建 MCP Server、Tool、Tool Call、Permission 的数据库模型。

### 任务清单

```text
[ ] 创建 models/mcp.py
[ ] 定义 McpServer ORM
[ ] 定义 McpTool ORM
[ ] 定义 McpToolCall ORM
[ ] 定义 McpPermission ORM
[ ] 创建 schemas/mcp.py
[ ] 创建 Alembic migration
[ ] 写基础数据库测试
```

### 完成标准

```text
可以保存一个 MCP Server 配置，并保存它发现到的工具。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(mcp): add mcp data models
```

---

## Step 3：实现 MCP Server Registry

### 要做什么

管理 MCP Server 的配置和状态。

### 任务清单

```text
[ ] 创建 mcp/server_registry.py
[ ] 实现 create_server()
[ ] 实现 update_server()
[ ] 实现 delete_server()
[ ] 实现 list_servers()
[ ] 实现 get_server()
[ ] 支持 trust_level
[ ] 支持 enabled / disabled
```

### 完成标准

```text
业务代码通过 ServerRegistry 管理 MCP Server，不直接操作 ORM。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(mcp): add server registry
```

---

## Step 4：实现 MCP Client 基础连接

### 要做什么

实现连接 MCP Server 的基础能力。

### 任务清单

```text
[ ] 创建 mcp/mcp_types.py
[ ] 创建 mcp/mcp_client.py
[ ] 支持 stdio transport
[ ] 预留 sse / http transport
[ ] 实现 initialize
[ ] 实现 list_tools
[ ] 实现 call_tool
[ ] 统一 MCPClientError
[ ] 记录连接状态和错误
```

### 初版建议

```text
优先支持 stdio MCP。
Filesystem MCP、SQLite MCP 和本地自定义 MCP Server 都可以先通过 stdio 跑通。
```

### 完成标准

```text
后端可以启动一个 stdio MCP Server，并调用 list_tools。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(mcp): implement stdio mcp client
```

---

## Step 5：实现 MCP Tool Discovery

### 要做什么

连接 MCP Server 后发现工具并写入数据库。

### 任务清单

```text
[ ] 创建 mcp/tool_discovery.py
[ ] 调用 MCP list_tools
[ ] 保存 tool name / description / schema
[ ] 默认 disabled 或 restricted
[ ] 推断 risk_level
[ ] 支持刷新工具列表
[ ] 记录 discover trace_step
```

### 风险等级推断建议

```text
只读查询：low
写文件 / 写数据库：medium
执行命令 / 删除 / 网络副作用：high
无法判断：medium
```

### 完成标准

```text
前端能看到某个 MCP Server 暴露了哪些工具。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(mcp): discover mcp tools
```

---

## Step 6：实现 MCP Permission Policy

### 要做什么

把 MCP 工具接入 Plan 5 的风险与审批体系。

### 任务清单

```text
[ ] 创建 mcp/permission_policy.py
[ ] 支持 server trust_level
[ ] 支持 tool enabled
[ ] 支持 requires_approval
[ ] 支持 path_allowlist
[ ] 支持 network_allowlist
[ ] 与 Tool Risk Policy 合并判断
[ ] 高风险 MCP Call 进入 Human Approval
```

### 完成标准

```text
不可信 MCP Server 的工具不会被 Agent 静默调用。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(mcp): add mcp permission policy
```

---

## Step 7：实现 MCP Tool Adapter

### 要做什么

把 MCP Tool 转换成 Agent Runtime 可调用的 Tool。

### 任务清单

```text
[ ] 创建 mcp/tool_adapter.py
[ ] 将 MCP input_schema 映射为 Tool Schema
[ ] 将 MCP Tool 注册到 Tool Registry
[ ] 支持 mcp_server_id / mcp_tool_id metadata
[ ] Runtime 调用时路由到 mcp_call_service
[ ] 输出统一 ToolResult
```

### 完成标准

```text
Agent Runtime 可以像调用内置工具一样调用 MCP Tool。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(mcp): adapt mcp tools into runtime tools
```

---

## Step 8：实现 MCP Tool Call Service

### 要做什么

统一执行 MCP Tool Call。

### 任务清单

```text
[ ] 创建 mcp/mcp_call_service.py
[ ] 调用 permission_policy
[ ] 必要时创建 approval_request
[ ] 调用 MCP client call_tool
[ ] 保存 mcp_tool_calls
[ ] 写入 trace_step
[ ] 统一错误处理和超时
```

### 完成标准

```text
一次 MCP Tool Call 可以被执行、审批、记录和复盘。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(mcp): execute mcp tool calls
```

---

## Step 9：实现 MCP API

### 要做什么

让前端可以管理 MCP Server 和工具。

### 任务清单

```text
[ ] 创建 api/v1/mcp.py
[ ] POST /api/v1/mcp/servers
[ ] GET /api/v1/mcp/servers
[ ] PUT /api/v1/mcp/servers/{server_id}
[ ] DELETE /api/v1/mcp/servers/{server_id}
[ ] POST /api/v1/mcp/servers/{server_id}/connect
[ ] POST /api/v1/mcp/servers/{server_id}/discover-tools
[ ] GET /api/v1/mcp/servers/{server_id}/tools
[ ] PUT /api/v1/mcp/tools/{tool_id}
[ ] POST /api/v1/mcp/tools/{tool_id}/call
```

### 完成标准

```text
Swagger 可以添加 MCP Server、发现工具并测试调用。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(mcp): add mcp api
```

---

## Step 10：实现 MCP 管理页面

### 要做什么

让用户可视化管理 MCP Server 和 MCP Tool。

### 页面功能

```text
[ ] MCP Server 列表
[ ] 新增 / 编辑 Server
[ ] 连接状态展示
[ ] 工具发现按钮
[ ] MCP Tool 表格
[ ] 启用 / 禁用工具
[ ] 风险等级展示
[ ] 权限配置
[ ] 测试调用
[ ] 跳转 Trace
```

### 组件建议

```text
McpPage
McpServerList
McpServerEditor
McpToolTable
McpPermissionPanel
McpToolCallPreview
```

### 完成标准

```text
用户可以通过前端配置 MCP，并控制哪些 MCP Tool 能被 Agent 调用。
```

### 预计时间

14～22 小时

### 建议 commit

```text
feat(frontend): add mcp management page
```

---

## Step 11：接入 Filesystem MCP

### 要做什么

接入一个文件系统 MCP Server。

### 任务清单

```text
[ ] 添加 Filesystem MCP Server 示例配置
[ ] 配置可信路径
[ ] 限制默认只读
[ ] 测试 list / read 类工具
[ ] 写文件类工具默认需要 approval
[ ] 删除类工具默认禁用
[ ] 增加 Demo 文档
```

### 完成标准

```text
Agent 可以通过 Filesystem MCP 读取可信路径下的文件。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(mcp): add filesystem mcp integration
```

---

## Step 12：接入 GitHub MCP

### 要做什么

接入 GitHub 相关 MCP 能力。

### 任务清单

```text
[ ] 添加 GitHub MCP Server 示例配置
[ ] 支持 token 从环境变量读取
[ ] 只读操作默认 low / medium
[ ] 创建 issue / comment / PR 等写操作需要 approval
[ ] 禁止静默 merge / delete
[ ] 写 GitHub MCP 使用文档
```

### 完成标准

```text
Agent 可以读取仓库、issue 或 PR 信息；写操作必须经过用户确认。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(mcp): add github mcp integration
```

---

## Step 13：接入 SQLite MCP

### 要做什么

让 Agent 能通过 MCP 查询本地 SQLite 数据库。

### 任务清单

```text
[ ] 添加 SQLite MCP Server 示例配置
[ ] 限制数据库路径必须在 trusted_paths 内
[ ] SELECT 默认允许
[ ] INSERT / UPDATE / DELETE 需要 approval
[ ] DROP / ALTER 默认禁用
[ ] 查询结果限制行数
```

### 完成标准

```text
Agent 可以安全查询本地 SQLite 数据库，并且危险 SQL 被拦截或审批。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(mcp): add sqlite mcp integration
```

---

## Step 14：实现自定义 MCP Server

### 要做什么

让 AI Agent Lab 自己也可以作为 MCP Server 暴露能力。

### 初版暴露能力

```text
search_knowledge_base
list_memories
create_agent_run
get_trace_run
```

### 任务清单

```text
[ ] 创建 mcp/custom_server.py
[ ] 暴露 tools/list
[ ] 暴露 tools/call
[ ] 将内部 API 包装为 MCP Tool
[ ] 写本地 stdio 启动脚本
[ ] 写使用文档
```

### 完成标准

```text
外部 MCP Client 可以调用 AI Agent Lab 的知识库检索和 Trace 查询能力。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(mcp): expose ai agent lab as mcp server
```

---

## Step 15：设计 Audio 数据模型

### 要做什么

创建语音文件、转写、合成、语音会话和语音回合表。

### 任务清单

```text
[ ] 创建 models/audio.py
[ ] 定义 AudioFile ORM
[ ] 定义 STTTranscript ORM
[ ] 定义 TTSOutput ORM
[ ] 定义 VoiceSession ORM
[ ] 定义 VoiceTurn ORM
[ ] 创建 schemas/audio.py
[ ] 创建 Alembic migration
[ ] 写基础数据库测试
```

### 完成标准

```text
系统可以保存录音文件、转写文本、TTS 输出和语音回合。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(voice): add audio data models
```

---

## Step 16：实现 Audio Storage

### 要做什么

保存录音和 TTS 音频文件。

### 任务清单

```text
[ ] 创建 voice/audio_storage.py
[ ] 设计 audio 文件目录
[ ] 校验 mime_type
[ ] 限制文件大小
[ ] 保存 AudioFile 记录
[ ] 支持读取音频文件
[ ] 支持删除音频文件
```

### 初版限制建议

```text
单次录音最长 2 分钟
单个音频文件最大 25MB
支持 wav / mp3 / webm
```

### 完成标准

```text
前端上传一段录音后，后端可以保存并返回 audio_file_id。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(voice): add audio storage
```

---

## Step 17：设计 STT Provider 抽象

### 要做什么

定义统一语音识别接口。

### 核心接口

```python
class BaseSTTProvider:
    async def transcribe(self, audio: bytes, language: str | None = None) -> STTResult:
        ...
```

### 任务清单

```text
[ ] 创建 providers/stt/base.py
[ ] 定义 STTResult
[ ] 定义 BaseSTTProvider
[ ] 定义 STTProviderError
[ ] 创建 providers/stt/registry.py
```

### 完成标准

```text
业务代码不直接依赖某一家 STT 服务。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(stt): add stt provider abstraction
```

---

## Step 18：实现 STT Provider

### 要做什么

接入一个可用 STT Provider。

### 初版建议

```text
优先实现 OpenAI-compatible STT 或 Whisper 本地封装。
如果本地依赖太重，先用 API Provider 跑通闭环。
```

### 任务清单

```text
[ ] 创建 providers/stt/openai_compatible.py
[ ] 支持 base_url
[ ] 支持 api_key
[ ] 支持 model
[ ] 支持 language
[ ] 解析 text / segments
[ ] 统一错误处理
[ ] 记录 latency
```

### 完成标准

```text
后端可以把一段音频转写成文本。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(stt): implement openai compatible stt provider
```

---

## Step 19：设计 TTS Provider 抽象

### 要做什么

定义统一语音合成接口。

### 核心接口

```python
class BaseTTSProvider:
    async def synthesize(self, text: str, voice: str, speed: float = 1.0) -> TTSResult:
        ...
```

### 任务清单

```text
[ ] 创建 providers/tts/base.py
[ ] 定义 TTSResult
[ ] 定义 BaseTTSProvider
[ ] 定义 TTSProviderError
[ ] 创建 providers/tts/registry.py
```

### 完成标准

```text
业务代码不直接依赖某一家 TTS 服务。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(tts): add tts provider abstraction
```

---

## Step 20：实现 TTS Provider

### 要做什么

接入一个可用 TTS Provider。

### 初版建议

```text
优先实现 Edge TTS。
它成本低，适合本地学习项目。
同时保留 OpenAI-compatible TTS 扩展点。
```

### 任务清单

```text
[ ] 创建 providers/tts/edge_tts_provider.py
[ ] 支持 voice
[ ] 支持 speed
[ ] 输出 mp3 或 wav
[ ] 保存 audio_files
[ ] 保存 tts_outputs
[ ] 统一错误处理
```

### 完成标准

```text
后端可以把文本合成为音频文件，并返回可播放 URL。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(tts): implement edge tts provider
```

---

## Step 21：实现 Voice API

### 要做什么

暴露录音、转写、合成和语音会话接口。

### 任务清单

```text
[ ] 创建 api/v1/voice.py
[ ] POST /api/v1/voice/audio-files
[ ] POST /api/v1/voice/transcribe
[ ] POST /api/v1/voice/tts
[ ] POST /api/v1/voice/sessions
[ ] GET /api/v1/voice/sessions
[ ] POST /api/v1/voice/turns
[ ] GET /api/v1/voice/providers
```

### 完成标准

```text
Swagger 可以上传音频、转写文本、合成语音并创建 voice turn。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(voice): add voice api
```

---

## Step 22：实现 Voice Pipeline

### 要做什么

把 STT、Agent Runtime 和 TTS 串起来。

### 流程

```text
record audio
    -> save audio
    -> STT
    -> create user message
    -> create agent_run
    -> get assistant text
    -> optional TTS
    -> save voice_turn
    -> return transcript + answer + audio
```

### 任务清单

```text
[ ] 创建 voice/voice_pipeline.py
[ ] 输入 audio_file_id
[ ] 调用 stt_service
[ ] 调用 agent_runtime
[ ] 可选调用 tts_service
[ ] 保存 voice_turn
[ ] 写入 trace_step
```

### 完成标准

```text
用户说一句话，系统可以转成文本并交给 Agent 回答。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(voice): add voice agent pipeline
```

---

## Step 23：实现前端录音和语音 UI

### 要做什么

让用户可以通过浏览器录音并发送给 Agent。

### 页面功能

```text
[ ] 麦克风按钮
[ ] 录音状态
[ ] 手动开始 / 停止
[ ] 上传 audio blob
[ ] 展示 transcript
[ ] 展示 assistant answer
[ ] 播放 TTS
[ ] Voice Turn 历史
```

### 组件建议

```text
VoicePage
VoiceRecorder
TranscriptPanel
TtsPlayer
VoiceTurnList
AudioProviderSettings
```

### 完成标准

```text
用户可以点麦克风说话，并看到转写和 Agent 回复。
```

### 预计时间

14～22 小时

### 建议 commit

```text
feat(frontend): add voice interface
```

---

## Step 24：实现基础 VAD

### 要做什么

减少用户手动停止录音的负担。

### 任务清单

```text
[ ] 创建 voice/vad.py
[ ] 支持前端音量阈值检测
[ ] 支持静音超时停止
[ ] 支持最大录音时长限制
[ ] 保留手动停止按钮
[ ] 记录 vad metadata
```

### 初版说明

```text
Plan 6 不要求复杂神经网络 VAD。
可以先做前端音量阈值 + 静音计时。
```

### 完成标准

```text
用户说完后，系统可以在短暂静音后自动停止录音。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(voice): add basic vad
```

---

## Step 25：设计 Media 数据模型

### 要做什么

创建图片、OCR、视觉分析相关数据模型。

### 任务清单

```text
[ ] 创建 models/media.py
[ ] 定义 MediaAsset ORM
[ ] 定义 OCRResult ORM
[ ] 定义 VisionAnalysis ORM
[ ] 创建 schemas/media.py
[ ] 创建 Alembic migration
[ ] 写基础数据库测试
```

### 完成标准

```text
系统可以保存图片资源、OCR 结果和 VLM 分析结果。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(multimodal): add media data models
```

---

## Step 26：实现 Media Upload

### 要做什么

支持上传图片和截图。

### 任务清单

```text
[ ] 创建 multimodal/media_service.py
[ ] 支持 png / jpg / jpeg / webp
[ ] 限制文件大小
[ ] 计算 hash
[ ] 读取宽高
[ ] 保存 media_assets
[ ] 返回 media_id
```

### 初版限制建议

```text
单张图片最大 10MB
单次最多上传 5 张
支持 png / jpg / jpeg / webp
```

### 完成标准

```text
前端可以上传图片，后端可以保存并展示预览。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(multimodal): add media upload
```

---

## Step 27：设计 OCR Provider 抽象

### 要做什么

定义统一 OCR 接口。

### 核心接口

```python
class BaseOCRProvider:
    async def extract_text(self, image: bytes) -> OCRResult:
        ...
```

### 任务清单

```text
[ ] 创建 providers/ocr/base.py
[ ] 定义 OCRBlock
[ ] 定义 OCRResult
[ ] 定义 BaseOCRProvider
[ ] 创建 providers/ocr/registry.py
```

### 完成标准

```text
业务代码不直接依赖某个 OCR 引擎。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(ocr): add ocr provider abstraction
```

---

## Step 28：实现 OCR Provider

### 要做什么

接入一个可用 OCR Provider。

### 初版建议

```text
优先使用轻量 API OCR 或本地 OCR。
如果本地 OCR 安装复杂，先用 Vision Provider 做 OCR fallback。
```

### 任务清单

```text
[ ] 创建 providers/ocr/api_ocr.py
[ ] 支持 base_url
[ ] 支持 api_key
[ ] 支持 image bytes
[ ] 解析 text / blocks
[ ] 保存 ocr_results
[ ] 统一错误处理
```

### 完成标准

```text
截图或图片可以提取文字。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(ocr): implement ocr provider
```

---

## Step 29：设计 Vision Provider 抽象

### 要做什么

定义统一 VLM 图片理解接口。

### 核心接口

```python
class BaseVisionProvider:
    async def analyze(self, prompt: str, images: list[bytes]) -> VisionAnalysisResult:
        ...
```

### 任务清单

```text
[ ] 创建 providers/vision/base.py
[ ] 定义 VisionAnalysisResult
[ ] 定义 BaseVisionProvider
[ ] 定义 VisionProviderError
[ ] 创建 providers/vision/registry.py
```

### 完成标准

```text
业务代码不直接依赖某个视觉模型。
```

### 预计时间

6～10 小时

### 建议 commit

```text
feat(vision): add vision provider abstraction
```

---

## Step 30：实现 Vision Provider

### 要做什么

接入一个 OpenAI-compatible 或 Qwen-VL 兼容视觉模型。

### 任务清单

```text
[ ] 创建 providers/vision/openai_compatible.py
[ ] 支持 base_url
[ ] 支持 api_key
[ ] 支持 model
[ ] 支持 image input
[ ] 支持 text prompt
[ ] 解析 result_text
[ ] 记录 token / cost / latency
```

### 完成标准

```text
后端可以让视觉模型分析一张图片或截图。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(vision): implement openai compatible vision provider
```

---

## Step 31：实现 Multimodal API

### 要做什么

暴露图片上传、OCR、VLM 和图文问答接口。

### 任务清单

```text
[ ] 创建 api/v1/multimodal.py
[ ] POST /api/v1/multimodal/media
[ ] GET /api/v1/multimodal/media
[ ] POST /api/v1/multimodal/media/{media_id}/ocr
[ ] POST /api/v1/multimodal/media/{media_id}/analyze
[ ] POST /api/v1/multimodal/chat
[ ] POST /api/v1/multimodal/media/{media_id}/add-to-knowledge-base
```

### 完成标准

```text
Swagger 可以上传图片、提取 OCR、调用视觉模型分析并进行图文问答。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(multimodal): add multimodal api
```

---

## Step 32：实现 Multimodal Prompt 和图文问答

### 要做什么

把图片和文本一起送给模型。

### 任务清单

```text
[ ] 创建 multimodal/multimodal_prompt.py
[ ] 支持单图 + 文本
[ ] 支持多图 + 文本
[ ] 支持 OCR 文本作为辅助上下文
[ ] 支持 RAG sources 作为辅助上下文
[ ] 记录 vision trace_step
```

### Prompt 建议

```text
请根据用户问题、图片内容和可选 OCR 文本回答。
如果图片中没有相关信息，请明确说明。
不要编造图片中不存在的细节。
```

### 完成标准

```text
用户上传截图后，可以追问截图中的错误、UI、图表或文字内容。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(multimodal): add image text chat
```

---

## Step 33：实现 OCR 结果入库

### 要做什么

让图片文字可以进入知识库。

### 任务清单

```text
[ ] 创建 multimodal/image_rag.py
[ ] 将 OCR text 转为 ParsedDocument
[ ] 保存为 document
[ ] 复用 Plan 3 chunking
[ ] 复用 embedding pipeline
[ ] metadata 标记 source_media_id
[ ] 前端支持 add-to-knowledge-base
```

### 完成标准

```text
用户上传截图或图片后，可以把 OCR 文本加入知识库并被 RAG 检索。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(multimodal): add ocr text to knowledge base
```

---

## Step 34：实现多模态前端页面

### 要做什么

让用户可以上传图片、OCR、分析和图文问答。

### 页面功能

```text
[ ] 图片上传
[ ] 图片预览
[ ] OCR 按钮
[ ] OCR 结果展示
[ ] VLM 分析按钮
[ ] 视觉分析结果展示
[ ] 图文问答输入框
[ ] OCR 入库按钮
[ ] 来源和 Trace 跳转
```

### 组件建议

```text
MultimodalPage
MediaUploadPanel
ImagePreview
OcrResultPanel
VisionAnalysisPanel
MultimodalSourceCard
```

### 完成标准

```text
用户可以在前端完成图片上传、OCR、图片分析和图文问答。
```

### 预计时间

14～22 小时

### 建议 commit

```text
feat(frontend): add multimodal page
```

---

## Step 35：设计桌面端技术方案

### 要做什么

确定桌面端壳、启动方式和本地权限模型。

### 推荐方案

```text
桌面壳：Tauri
前端：复用现有 React 构建产物
后端：本地 FastAPI 进程或用户手动启动
配置：本地 JSON + 后端 settings 表
权限：trusted_paths + Human Approval
```

### 任务清单

```text
[ ] 创建 desktop/README.md
[ ] 记录 Tauri 方案
[ ] 记录本地后端启动方案
[ ] 记录可信路径权限模型
[ ] 记录打包限制
```

### 完成标准

```text
桌面端不是临时套壳，而是有明确的启动、配置和权限设计。
```

### 预计时间

4～8 小时

### 建议 commit

```text
docs(desktop): design desktop app approach
```

---

## Step 36：创建 Tauri 桌面壳

### 要做什么

让 React WebUI 能作为桌面应用运行。

### 任务清单

```text
[ ] 创建 desktop/package.json
[ ] 初始化 src-tauri
[ ] 配置 tauri.conf.json
[ ] 指向前端构建产物
[ ] 配置应用名称和窗口大小
[ ] 本地启动测试
```

### 完成标准

```text
Windows 上可以打开 AI Agent Lab 桌面窗口，并加载现有前端。
```

### 预计时间

8～12 小时

### 建议 commit

```text
feat(desktop): add tauri desktop shell
```

---

## Step 37：实现本地配置与 Desktop API

### 要做什么

管理桌面端配置、后端连接和可信路径。

### 任务清单

```text
[ ] 创建 models/desktop.py
[ ] 定义 DesktopSetting ORM
[ ] 定义 TrustedPath ORM
[ ] 创建 desktop/local_config.py
[ ] 创建 desktop/trusted_paths.py
[ ] 创建 api/v1/desktop.py
[ ] GET /api/v1/desktop/status
[ ] GET /api/v1/desktop/settings
[ ] POST /api/v1/desktop/trusted-paths
[ ] POST /api/v1/desktop/validate-path
```

### 完成标准

```text
用户可以配置可信本地目录，Agent 只能访问允许范围。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(desktop): add local config and trusted paths
```

---

## Step 38：实现 Desktop Settings 页面

### 要做什么

让用户配置桌面端本地能力。

### 页面功能

```text
[ ] 桌面端连接状态
[ ] 本地后端状态
[ ] 可信路径列表
[ ] 新增 / 删除可信路径
[ ] 权限级别设置
[ ] 快捷键设置
[ ] MCP 本地路径提示
```

### 组件建议

```text
DesktopSettingsPage
TrustedPathList
HotkeySettings
DesktopStatusPanel
LocalConfigEditor
```

### 完成标准

```text
用户可以在页面上管理本地路径和桌面端设置。
```

### 预计时间

10～16 小时

### 建议 commit

```text
feat(frontend): add desktop settings page
```

---

## Step 39：实现系统托盘和快捷键

### 要做什么

让桌面端更像日常工具。

### 任务清单

```text
[ ] 创建 desktop/src-tauri/src/tray.rs
[ ] 创建 desktop/src-tauri/src/hotkeys.rs
[ ] 支持系统托盘显示 / 隐藏窗口
[ ] 支持全局快捷键唤起窗口
[ ] 支持快捷键打开语音输入
[ ] 支持设置项控制是否启用
```

### 初版建议

```text
默认快捷键可以是 Ctrl+Alt+Space。
如果冲突，允许用户关闭或修改。
```

### 完成标准

```text
用户可以用快捷键唤起桌面端，并从托盘显示或退出应用。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(desktop): add tray and global hotkey
```

---

## Step 40：接入 Desktop 本地文件权限

### 要做什么

把 trusted_paths 接入文件工具和 Filesystem MCP。

### 任务清单

```text
[ ] 创建 desktop/desktop_permissions.py
[ ] 校验路径是否在 trusted_paths 内
[ ] 读操作要求 read 权限
[ ] 写操作要求 write 权限和 approval
[ ] 执行操作要求 execute 权限和 approval
[ ] Filesystem MCP 调用前检查路径
[ ] 违规访问写入 trace_step
```

### 完成标准

```text
Agent 不能越过可信路径访问本地文件。
```

### 预计时间

8～14 小时

### 建议 commit

```text
feat(desktop): enforce trusted path permissions
```

---

## Step 41：打包桌面端

### 要做什么

生成可安装或可运行的 Windows 桌面包。

### 任务清单

```text
[ ] 配置 Tauri build
[ ] 配置图标
[ ] 配置应用名称
[ ] 配置版本号 v0.6.0
[ ] 生成 Windows 构建产物
[ ] 写安装和启动说明
```

### 完成标准

```text
Windows 上可以从构建产物启动 AI Agent Lab。
```

### 预计时间

6～12 小时

### 建议 commit

```text
chore(desktop): package windows desktop app
```

---

## Step 42：补充 Plan 6 测试

### 要做什么

给 MCP、Voice、Multimodal、Desktop 写基础测试。

### 测试范围

```text
[ ] MCP Server Registry 测试
[ ] MCP Client mock 测试
[ ] MCP Tool Discovery 测试
[ ] MCP Permission Policy 测试
[ ] MCP Tool Adapter 测试
[ ] MCP Tool Call Service 测试
[ ] Audio Storage 测试
[ ] STT Provider mock 测试
[ ] TTS Provider mock 测试
[ ] Voice Pipeline mock 测试
[ ] Media Upload 测试
[ ] OCR Provider mock 测试
[ ] Vision Provider mock 测试
[ ] Multimodal Prompt 测试
[ ] OCR 入库测试
[ ] Trusted Path 权限测试
[ ] Desktop API 测试
```

### 完成标准

```text
核心集成逻辑不依赖真实 MCP Server、真实 STT/TTS/VLM 服务也能用 mock 跑通。
```

### 预计时间

16～24 小时

### 建议 commit

```text
test(workspace): add mcp voice vision desktop tests
```

---

## Step 43：补充 Plan 6 文档

### 要做什么

写清楚 Agent 工作台的外部能力设计。

### 文档建议

```text
docs/30-plan-6-agent-workspace.md
docs/31-mcp-client.md
docs/32-mcp-permissions.md
docs/33-custom-mcp-server.md
docs/34-voice-agent.md
docs/35-stt-tts-providers.md
docs/36-multimodal-vision.md
docs/37-ocr-to-rag.md
docs/38-desktop-app.md
docs/39-local-permissions.md
```

### 每篇文档写什么

```text
1. 模块目标
2. 为什么这样设计
3. 核心数据结构
4. API 说明
5. 当前限制
6. 与 Agent Runtime / Trace / Human Approval 的关系
7. 如何演示
```

### 完成标准

```text
别人看文档能理解：
MCP 如何接入 Runtime；
外部工具权限如何控制；
语音如何进入 Agent；
图片和 OCR 如何进入问答和 RAG；
桌面端如何限制本地文件访问。
```

### 预计时间

10～16 小时

### 建议 commit

```text
docs: add plan 6 agent workspace documents
```

---

## Step 44：Plan 6 封版

### 要做什么

发布 v0.6.0。

### 任务清单

```text
[ ] 更新 README
[ ] 更新 CHANGELOG.md
[ ] 截图 MCP 管理页面
[ ] 截图 MCP Tool Call Trace
[ ] 截图 Voice 页面
[ ] 截图 Multimodal 页面
[ ] 截图 Desktop Settings 页面
[ ] 截图桌面端窗口
[ ] 记录当前支持的 MCP Transport
[ ] 记录当前支持的 STT / TTS Provider
[ ] 记录当前支持的 Vision / OCR Provider
[ ] 记录当前桌面端限制
[ ] 创建 Git tag：v0.6.0
```

### 完成标准

```text
从 README 启动项目后，可以完成：
1. 配置一个 MCP Server
2. 发现 MCP Tools
3. 启用一个低风险 MCP Tool
4. 通过 Agent 调用 MCP Tool
5. 对高风险 MCP Tool Call 做 Human Approval
6. 查看 MCP Tool Call Trace
7. 用麦克风输入问题
8. 查看 STT 转写结果
9. 让 Agent 回答语音输入
10. 播放 TTS 输出
11. 上传截图或图片
12. 对图片执行 OCR
13. 调用 VLM 分析图片
14. 基于图片进行图文问答
15. 将 OCR 文本加入知识库
16. 在桌面端打开应用
17. 配置可信本地路径
18. 通过桌面端快捷键唤起应用
19. 从托盘隐藏和恢复应用
```

### 建议 commit

```text
chore: release v0.6.0 agent workspace
```

---

## 11. Plan 6 最终验收标准

Plan 6 完成后，必须满足：

```text
[ ] mcp_servers 表可用
[ ] mcp_tools 表可用
[ ] mcp_tool_calls 表可用
[ ] mcp_permissions 表可用
[ ] MCP Server Registry 可用
[ ] MCP stdio Client 可用
[ ] MCP Tool Discovery 可用
[ ] MCP Permission Policy 可用
[ ] MCP Tool Adapter 可用
[ ] MCP Tool Call Service 可用
[ ] MCP API 可用
[ ] MCP 管理页面可用
[ ] Filesystem MCP 可用
[ ] GitHub MCP 可配置
[ ] SQLite MCP 可配置
[ ] 自定义 MCP Server 可用
[ ] STT Provider 抽象完成
[ ] 至少一个 STT Provider 可用
[ ] TTS Provider 抽象完成
[ ] 至少一个 TTS Provider 可用
[ ] Voice API 可用
[ ] Voice Pipeline 可用
[ ] 前端录音可用
[ ] TTS 播放可用
[ ] 基础 VAD 可用
[ ] media_assets 表可用
[ ] OCR Provider 抽象完成
[ ] 至少一个 OCR Provider 可用
[ ] Vision Provider 抽象完成
[ ] 至少一个 Vision Provider 可用
[ ] Multimodal API 可用
[ ] 图文问答可用
[ ] OCR 结果可加入知识库
[ ] Multimodal 页面可用
[ ] Tauri 桌面端可启动
[ ] Desktop API 可用
[ ] trusted_paths 可用
[ ] Desktop Settings 页面可用
[ ] 系统托盘可用
[ ] 全局快捷键可用
[ ] 本地文件权限检查可用
[ ] 核心测试已补充
[ ] README 已更新
[ ] docs 已更新
[ ] 已创建 v0.6.0 tag
```

---

## 12. Plan 6 最小可交付版本

如果时间不够，Plan 6 最小版本只做：

```text
1. MCP Server 数据模型
2. MCP stdio Client
3. MCP Tool Discovery
4. MCP Tool Adapter
5. MCP Permission Policy
6. MCP API
7. MCP 管理页面
8. Filesystem MCP 只读接入
9. STT Provider 抽象
10. 一个 STT Provider
11. 前端录音
12. Voice Pipeline 文本回复
13. TTS Provider 抽象
14. 一个 TTS Provider
15. Media Upload
16. OCR Provider 抽象
17. 一个 OCR Provider
18. Vision Provider 抽象
19. 一个 Vision Provider
20. 图片分析页面
21. Tauri 桌面壳
22. Trusted Paths
23. README 和文档更新
```

可以延期：

```text
1. GitHub MCP
2. SQLite MCP
3. 自定义 MCP Server
4. MCP SSE / HTTP transport
5. 语音自动打断
6. 流式 TTS
7. 复杂 VAD
8. OCR 入库完整 UI
9. 系统托盘
10. 全局快捷键
11. 桌面端自动启动后端
12. Windows 安装包优化
```

不能延期：

```text
1. MCP Client 基础能力
2. MCP 工具权限边界
3. MCP 接入 Agent Runtime
4. STT 输入闭环
5. TTS 输出闭环
6. 图片上传和分析
7. 桌面端基础壳
8. 本地可信路径
```

如果按最小版本进入后续多 Agent 扩展，必须先补齐以下桥接项：

```text
1. MCP Tool Adapter 能把外部工具统一映射为 Runtime Tool
2. Human Approval 可以覆盖 Filesystem MCP、本地文件访问和付费 API 调用
3. Trace Timeline 可以展示文字、语音、图片、MCP Tool Call 的统一执行过程
4. Desktop Trusted Paths 和 Web 工具权限边界保持同一套策略
5. Voice / Vision 输入最终都能转成 Agent Runtime 可处理的任务上下文
```

---

## 13. Plan 6 与后续多 Agent 扩展的衔接

Plan 6 完成后，项目具备：

```text
基础 Chat
多模型 Provider
Tool Calling
知识库系统
Advanced RAG
Trace Timeline
Evaluation
Memory
Context Engine
Agent Runtime
Human Approval
MCP Client
MCP Tool Ecosystem
Voice Agent
STT / TTS
OCR / VLM
Multimodal Chat
Desktop App
Local Trusted Paths
```

这为后续 Phase 9 的多 Agent 扩展打基础。

后续多 Agent 不需要重新做：

```text
Tool Registry
MCP Tool Adapter
Human Approval
Trace Timeline
Memory
Context Engine
Voice Pipeline
Multimodal Input
Desktop Shell
```

后续可以继续扩展：

```text
Planner Agent
Research Agent
Coding Agent
Critic Agent
Summary Agent
Agent Handoff
Agent Communication
A2A
Computer Use
Browser Use
GraphRAG
Plugin Marketplace
```

换句话说：

```text
Plan 5 让 Agent Runtime 成型。
Plan 6 让 Runtime 进入真实工作台。
后续多 Agent 让多个 Runtime 角色协作。
```

---

## 14. Plan 6 完成后的简历表达

可以写成：

```text
在 AI Agent Lab 中设计并实现 Agent 工作台扩展，将核心 Agent Runtime 接入 MCP 工具生态、语音交互、多模态图片理解和桌面端。本阶段实现 MCP Client、工具发现、权限控制、MCP Tool Adapter 和自定义 MCP Server，使 Agent 能安全调用 Filesystem / GitHub / SQLite 等外部工具；同时实现 STT / TTS Provider、Voice Agent Pipeline、OCR / Vision Provider、图片问答、OCR 入库和 Tauri 桌面端，支持可信本地路径、系统托盘、快捷键和完整 Trace 复盘。
```

亮点可以拆成：

```text
1. 设计 MCP Client 和 Tool Adapter，将外部 MCP Tools 统一接入 Agent Runtime 与 Human Approval。
2. 实现 MCP 权限体系，支持 Server Trust Level、Tool Risk Level、可信路径和高风险操作审批。
3. 构建 Voice Agent Pipeline，支持录音、STT、Agent Runtime 调用、TTS 播放和语音回合记录。
4. 实现多模态输入能力，支持图片上传、OCR、VLM 分析、图文问答和 OCR 结果进入知识库。
5. 使用 Tauri 构建桌面端，使 AI Agent Lab 支持本地配置、可信路径、系统托盘和全局快捷键。
```

---

## 15. Plan 6 实施建议

Plan 6 是项目从“技术参考实现”走向“可日常使用工作台”的阶段。

推荐执行顺序：

```text
先做 MCP 基础设施
再做 MCP 权限和前端管理
再做语音输入输出闭环
再做图片 / OCR / VLM 闭环
最后做桌面端和本地权限
```

不要一开始就追求完整桌面产品。

Plan 6 的关键不是堆更多入口，而是让每种入口都能复用同一个 Runtime：

```text
文字输入进入 Agent Runtime
语音转文字后进入 Agent Runtime
图片分析结果进入 Agent Runtime
MCP 工具调用受 Agent Runtime 调度
桌面端只是 Runtime 的本地使用形态
```

这样项目不会变成多个互不相干的 Demo。

Plan 6 完成后，AI Agent Lab 的形态会非常清晰：

```text
一个可观察、可评测、可扩展、可日常使用的 AI Engineering Workspace。
```
