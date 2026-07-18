# Plan 2 M1/M2 审计问题修复设计

## 1. 背景与目标

Plan 2 Milestone 1 和 Milestone 2 的独立审计发现 6 个代码缺陷、若干直接关联的测试缺口，以及 2 个文档错漏。当前修复批次只处理这些已确认问题，目标是在不进入 P2-M3、不新增后续 Plan 能力的前提下，重新建立文件系统安全边界、Tool/Registry 稳定契约和 Agent 审计数据一致性，并让文档与实际交付保持一致。

本批次不得调用真实 Provider、真实网络 Tool 或付费服务，不得读取真实敏感文件或用户数据库。SQLite 继续作为默认且长期支持的主数据库。

## 2. 方案比较与选择

### 方案 A：按根因做增量修复（采用）

- 在现有安全模块增加跨平台的 link-like/reparse point 判断和精确的凭据名称策略。
- 保持 Tool 抽象和 Registry 的现有职责，只收紧定义不可变性与参数 schema 边界。
- 使用新的 Alembic revision 增加 AgentRun/Message 复合一致性约束，不改写已提交迁移。
- 用失败测试逐项锁定审计复现，再实施最小修复。

优点是 diff 边界清晰、兼容现有调用方、可以独立验证，也符合 1～3 个连续 Step 的批次规则。

### 方案 B：重构整个 Tool 与文件系统访问层（不采用）

可以引入平台专用文件系统适配器、统一权限执行器和不可变 ToolDefinition/ToolExecutor 双层模型，但会提前侵入 M3 Agent Loop 和后续权限执行职责，范围和回归风险明显过大。

### 方案 C：只记录限制（不采用）

无法解决 junction 越界、凭据泄露和跨会话数据错误，不能重新打开 M3 readiness gate。

## 3. 修复范围与三步拆分

### Step 1：文件系统安全和列表正确性

安全模块维护两类敏感名称：明确的敏感目录组件，以及明确的凭据文件名/后缀。名称比较继续使用 Windows 兼容的尾随空格/点归一化和大小写折叠。普通 `.gitignore` 等非凭据隐藏文件保持可见。

首批新增拒绝项覆盖审计已经复现的 `.npmrc`、`.pypirc`、`.netrc`、`_netrc`、`.git-credentials`、`credentials.json`、`secrets.toml` 和 `.aws`，并覆盖同类高置信目录 `.azure`、`.kube`、`.docker`、`.gnupg`、`.password-store` 以及 `gcloud`。同时覆盖常见云凭据文件 `application_default_credentials.json`、`client_secret.json`、`service-account.json` 和 `service_account.json`。策略保持精确枚举，不封禁所有 dotfile 或所有包含 `secret` 的普通名称。

安全模块提供 link-like 判断：普通 symlink 或 Windows `FILE_ATTRIBUTE_REPARSE_POINT` 均视为不可递归条目。`list_dir` 报告其为 `symlink`，但绝不进入目标。这个兼容名称避免改变现有 ToolResult schema；设计文档说明该类型也包含 junction 等 reparse point。

`list_dir` 的截断语义调整为“确实存在至少一个未返回的可见条目”才标记 `truncated=true`。遍历可以收集到 `max_entries + 1` 个可见条目作为 look-ahead，最终只返回前 `max_entries` 个，从而区分精确命中上限和真实截断。敏感条目和无法识别的条目不计入上限。

### Step 2：Tool 和 Registry 契约

Tool 将规范化后的 `name`、`description`、`permission_level`、`timeout_seconds` 和参数 schema 存入私有字段，并通过只读 property 暴露。参数 schema 每次读取都返回深拷贝，调用方修改返回值不会改变 Tool 内部定义；给只读 property 赋值会抛出 `AttributeError`。

Registry 继续保存可执行 Tool 实例，保持 `get_tool()` 和 `list_tools()` 的现有 API。因为公开定义不可变且 schema 防御性复制，注册键、执行实例和 OpenAI function schema 不再漂移。

通用 Tool 参数契约要求根 schema 明确为 `type: object`；Registry 注册时继续原子校验。schema 还必须能够被标准 JSON 序列化，防止合法性检查通过但 Provider payload 无法编码。Tool 名称收紧为最多 64 个字符，仅允许 ASCII 字母、数字、下划线和连字符，以满足现有 OpenAI-compatible exporter 的稳定函数名边界。ToolResult 中的外部 Provider tool name 继续由 schema 层按原有 100 字符限制接收，避免破坏响应兼容性。

### Step 3：Agent 数据一致性、迁移与文档

Message 增加命名唯一约束 `(id, conversation_id)`，作为复合外键的父键。AgentRun 移除 `user_message_id -> messages.id` 的单列外键，改为 `(user_message_id, conversation_id) -> messages(id, conversation_id)`，保留 `ON DELETE SET NULL`。由于 SQLite 的 `SET NULL` 会同时作用于复合外键列，而 `conversation_id` 不可为空且不能被清空，复合外键不能直接使用 `SET NULL`。

因此采用以下可执行语义：AgentRun 保留独立的 `conversation_id -> conversations.id ON DELETE CASCADE`；Message 删除行为由 ORM/数据库显式处理，只将可空的 `user_message_id` 设为 NULL，同时复合外键使用 `ON DELETE RESTRICT`。在删除 Message 前，ORM relationship 负责将关联 AgentRun 的 `user_message_id` 清空；数据库直接删除仍受到约束保护，避免隐式清空 `conversation_id`。现有“删除用户消息但保留 Agent 审计记录”的行为必须继续通过测试。

新增 Alembic revision，不改写 `20260717_0002`。升级前查询是否存在跨会话或悬空的 AgentRun/Message 记录；若存在，迁移以不包含用户内容的稳定错误停止，不静默修正历史数据。随后通过 batch operations 添加父唯一约束并替换外键。降级恢复单列外键并移除父唯一约束。所有迁移测试只使用全新临时 SQLite；从旧 revision 人工插入跨会话和悬空关联后，都必须验证升级 fail-closed。

文档更新范围包括：README/README_CN 的迁移表、Tool Calling 设计文档的 reparse/凭据/不可变 schema 约定、Plan 2 执行表的已完成 checklist 和审计修复记录，以及 CHANGELOG 的 Unreleased 修复项。

## 4. 错误和安全语义

- `read_file`、`list_dir` 对新增敏感名称继续返回现有安全错误，不回显被拒绝路径或凭据内容。
- reparse point 作为目录条目可以显示名称和 `symlink` 类型，但不显示目标，也不递归。
- Tool schema 注册失败继续抛出 `ToolSchemaError`，错误不回显 schema 中可能含有的值。
- 跨会话迁移失败只报告检测到不一致记录及修复方向，不输出 Message 内容、路径或 secret。
- 不引入工具执行超时、权限执行器、Agent Loop 或 Provider tool calling；这些仍属于后续 Step。

## 5. 测试策略

所有行为改动遵循 RED → GREEN → REFACTOR：

1. 安全测试先证明新增凭据名称当前可通过，再让其被拒绝；`read_file` 和 `list_dir` 使用合成内容。
2. Windows-only 测试创建工作区内 junction 指向工作区外的临时兄弟目录，证明当前会递归看到合成 marker；修复后只报告 junction 自身。若操作系统不是 Windows 则跳过；Windows 上只有明确不支持 junction 时才跳过。测试结束使用非递归 `os.rmdir()` 删除 junction，避免清理时跟随目标。
3. 精确条目上限测试先证明 `truncated` 误报，再验证 look-ahead 语义。
4. Tool 测试先证明公开属性和返回 schema 可改变内部契约，再验证只读 property 与深拷贝。
5. Registry/validation 测试覆盖非 object 根 schema、不可 JSON 序列化 schema 和非法 Provider function name。
6. ORM 测试证明跨 Conversation Message 被数据库拒绝，同时保留正常关系和删除行为。
7. 迁移测试检查新约束、升级、降级、重新升级，以及旧 revision 中不一致数据的 fail-closed 行为。

定向测试通过后运行后端完整 pytest、`pip check`、前端 typecheck/Vitest/build、全新临时 SQLite 的 Alembic upgrade/current/check/downgrade/re-upgrade，以及不调用 Provider 的 FastAPI health/OpenAPI/request-id smoke。

## 6. 非目标与接受限制

- 不实现 P2-M3 Provider tools、Agent Loop 或超时执行。
- 不实现 `web_fetch`、Shell Tool、write/delete file、RAG、Memory、MCP 或多模态能力。
- 不针对拥有本机特权、能在检查后替换路径的攻击者设计完整 TOCTOU 防御；本批次只修复稳定可利用的 reparse/junction 遍历。
- 不迁移到 PostgreSQL，不访问或修改用户现有 SQLite。
- 不创建提交；用户在验证和复审后手动 commit。

## 7. 完成标准

审计中的 6 个代码缺陷都有先失败后通过的回归测试，2 个文档错漏已同步；完整后端、前端、迁移和 smoke 验证通过；Git diff 只包含本修复批次，不含 secrets、生成物或跨 Plan 能力。Codex self-review 无阻塞项后即可进入 P2-M3-S1～S3。依据 2026-07-18 用户决定，不再执行 Claude Code secondary review；全部 6 个 Plan 和整个项目完成后，再由用户决定是否使用 Fable 5 做一次全项目检查。
