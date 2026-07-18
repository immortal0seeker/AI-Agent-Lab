# Plan 2 M1/M2 Audit Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Plan 2 M1/M2 审计确认的全部代码、测试和文档问题，使文件访问安全边界、Tool/Registry 契约与 Agent 审计数据约束达到进入 M3 前的要求。

**Architecture:** 在既有模块边界内做增量修复：`security.py` 负责敏感名称和 reparse point 分类，Tool 本身负责定义不可变性，Registry/validation 负责可注册 schema 边界，新 Alembic revision 负责跨表数据一致性。所有行为改变均由失败测试先行证明，不实现 M3 Agent Loop 或 Provider tool calling。

**Tech Stack:** Python 3.11、FastAPI、Pydantic v2、jsonschema Draft 2020-12、SQLAlchemy 2、Alembic、SQLite、pytest；React/TypeScript/Vitest/Vite 只做回归验证。

## Global Constraints

- 只处理审计确认的 M1/M2 问题，不进入 P2-M3 或后续 Plan。
- SQLite 是默认且长期支持的主数据库；新约束必须同时适用于 SQLite 和合理的 SQLAlchemy/Alembic 可移植性。
- 不读取、迁移、删除或重建 `backend/ai_agent_lab.db` 或任何用户数据库。
- 不读取真实 `.env`、凭据、SSH key、浏览器或系统凭据；安全测试只用合成内容。
- 不调用真实 Provider、真实网络 Tool 或付费服务。
- 必要代码注释使用中文，只解释非显然的安全或迁移意图。
- 不创建分支，不 stage、commit、push 或 tag；用户在验收后手动 commit。

---

### Task 1: Harden filesystem safety and list truncation

**Files:**
- Modify: `backend/app/tools/security.py`
- Modify: `backend/app/tools/builtin/list_dir.py`
- Modify: `backend/tests/test_tool_security.py`
- Modify: `backend/tests/test_tool_read_file.py`
- Modify: `backend/tests/test_tool_list_dir.py`

**Interfaces:**
- Consumes: `resolve_workspace_path()`、`is_sensitive_path_component()`、`ListDirTool._walk_directory()`。
- Produces: `is_reparse_point(path_stat: os.stat_result) -> bool`；敏感组件精确枚举；`truncated` 仅表示存在未返回的可见条目。

- [ ] **Step 1: 写敏感凭据路径的失败测试**

在 `test_tool_security.py` 增加：

```python
@pytest.mark.parametrize(
    "unsafe_path",
    [
        ".npmrc",
        ".pypirc",
        ".netrc",
        "_netrc",
        ".git-credentials",
        "credentials.json",
        "secrets.toml",
        ".aws/credentials",
        ".azure/accessTokens.json",
        ".kube/config",
        ".docker/config.json",
        ".gnupg/private-keys-v1.d/key",
        ".password-store/example.gpg",
        ".config/gcloud/application_default_credentials.json",
        "client_secret.json",
        "service-account.json",
        "service_account.json",
    ],
)
def test_resolve_workspace_path_rejects_credential_paths(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)
```

在 `test_tool_read_file.py` 和 `test_tool_list_dir.py` 分别用内容为 `synthetic-token` 的临时 `.npmrc` 证明读取被拒绝、目录结果不包含名称或内容。

- [ ] **Step 2: 运行敏感路径测试并确认 RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_security.py::test_resolve_workspace_path_rejects_credential_paths tests/test_tool_read_file.py tests/test_tool_list_dir.py::test_list_dir_filters_sensitive_entries_before_traversal -q
```

Expected: 新增 credential path 断言失败，`.npmrc` 仍可读/可列出；既有测试继续通过。

- [ ] **Step 3: 实施精确敏感名称策略**

在 `security.py` 将目录和文件分开维护：

```python
_SENSITIVE_DIRECTORY_NAMES = frozenset(
    {
        ".aws",
        ".azure",
        ".docker",
        ".git",
        ".gnupg",
        ".kube",
        ".password-store",
        ".ssh",
        "__pycache__",
        "docs-local",
        "gcloud",
    }
)
_SENSITIVE_FILE_NAMES = frozenset(
    {
        ".git-credentials",
        ".netrc",
        ".npmrc",
        ".pypirc",
        "_netrc",
        "application_default_credentials.json",
        "client_secret.json",
        "credentials.json",
        "secrets.toml",
        "service-account.json",
        "service_account.json",
    }
)
```

`is_sensitive_path_component()` 同时检查两个集合，并保留 `.env`、私钥名、`.pem`、`.key` 规则。不得封禁 `.gitignore` 或所有 dotfile。

- [ ] **Step 4: 运行敏感路径定向测试并确认 GREEN**

重复 Step 2 命令，Expected: 全部通过。

- [ ] **Step 5: 写 junction/reparse point 失败测试**

在 `test_tool_list_dir.py` 增加 Windows-only helper 和测试：

```python
def create_windows_junction(link: Path, target: Path) -> None:
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        pytest.skip("directory junctions are unavailable in this environment")


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse-point regression")
def test_list_dir_reports_but_never_follows_directory_junction(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "synthetic-marker.txt").write_text("safe", encoding="utf-8")
    junction = workspace / "junction-out"
    create_windows_junction(junction, outside)
    try:
        result = run_tool(
            ListDirTool(workspace_root=workspace),
            {"path": ".", "max_depth": 3},
        )
        paths = {entry["path"] for entry in result.data["entries"]}
        linked = next(
            entry
            for entry in result.data["entries"]
            if entry["path"] == "junction-out"
        )
        assert linked["type"] == "symlink"
        assert "junction-out/synthetic-marker.txt" not in paths
    finally:
        if junction.exists():
            os.rmdir(junction)
```

- [ ] **Step 6: 运行 junction 测试并确认 RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_list_dir.py::test_list_dir_reports_but_never_follows_directory_junction -q
```

Expected on Windows: FAIL because marker 被递归返回。非 Windows：SKIP。

- [ ] **Step 7: 实施 reparse point 分类**

在 `security.py` 新增：

```python
def is_reparse_point(path_stat: os.stat_result) -> bool:
    file_attributes = getattr(path_stat, "st_file_attributes", 0)
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(file_attributes & reparse_attribute)
```

在 `list_dir.py` 对每个 `DirEntry` 只取一次 `child.stat(follow_symlinks=False)`；普通 symlink 或 `is_reparse_point(child_stat)` 都设为 `type="symlink"`，不进入递归。目录和文件类型改用 `stat.S_ISDIR(child_stat.st_mode)` 与 `stat.S_ISREG(child_stat.st_mode)` 判断。

- [ ] **Step 8: 重跑 junction 与既有 symlink 测试并确认 GREEN**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_list_dir.py -q
```

Expected: Windows junction 与普通 symlink 均只报告自身；完整文件通过。

- [ ] **Step 9: 写精确上限失败测试**

```python
def test_list_dir_does_not_report_truncation_at_exact_entry_limit(
    tmp_path: Path,
) -> None:
    for name in ["a.txt", "b.txt"]:
        (tmp_path / name).write_text(name, encoding="utf-8")

    result = run_tool(
        ListDirTool(workspace_root=tmp_path, max_entries=2),
        {"path": "."},
    )

    assert result.metadata["entry_count"] == 2
    assert result.metadata["truncated"] is False
```

- [ ] **Step 10: 运行精确上限测试并确认 RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_list_dir.py::test_list_dir_does_not_report_truncation_at_exact_entry_limit -q
```

Expected: FAIL，当前返回 `truncated=True`。

- [ ] **Step 11: 用一个可见条目的 look-ahead 修复截断语义**

`_walk_directory()` 在 append 后只在 `len(entries) > self.max_entries` 时返回 `True`。`_list_dir()` 在递归结束后、排序前执行：

```python
if truncated:
    del entries[self.max_entries :]
```

这使真实多余条目触发截断，而精确等于上限时正常完成遍历并返回 `False`。

- [ ] **Step 12: 运行 Task 1 全部定向测试**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_security.py tests/test_tool_read_file.py tests/test_tool_list_dir.py -q
```

Expected: 全部通过；Windows junction 测试通过，其他平台仅该测试跳过。

---

### Task 2: Make Tool definitions immutable and schemas provider-safe

**Files:**
- Modify: `backend/app/tools/base.py`
- Modify: `backend/app/tools/validation.py`
- Modify: `backend/tests/test_tool_base.py`
- Modify: `backend/tests/test_tool_registry.py`
- Modify: `backend/tests/test_tool_validation.py`

**Interfaces:**
- Consumes: Tool 构造参数、`validate_tool_schema()`、Registry 现有注册/查找/导出 API。
- Produces: Tool 只读 metadata property；每次读取参数 schema 返回深拷贝；根 object 且 JSON 可序列化的注册边界；最多 64 字符的稳定函数名。

- [ ] **Step 1: 写 Tool metadata/schema 不可变性失败测试**

在 `test_tool_base.py` 增加：

```python
@pytest.mark.parametrize(
    ("field_name", "new_value"),
    [
        ("name", "renamed"),
        ("description", "changed"),
        ("permission_level", "write"),
        ("timeout_seconds", 99.0),
        ("parameters_schema", {"type": "string"}),
    ],
)
def test_tool_definition_fields_are_read_only(
    field_name: str,
    new_value: object,
) -> None:
    tool = build_tool()
    with pytest.raises(AttributeError):
        setattr(tool, field_name, new_value)


def test_tool_returns_defensive_parameter_schema_copy() -> None:
    tool = build_tool()
    exposed = tool.parameters_schema
    exposed["properties"]["value"]["type"] = "integer"
    assert tool.parameters_schema["properties"]["value"]["type"] == "string"
```

- [ ] **Step 2: 运行不可变性测试并确认 RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py::test_tool_definition_fields_are_read_only tests/test_tool_base.py::test_tool_returns_defensive_parameter_schema_copy -q
```

Expected: public attributes 可写、返回 schema 可修改内部状态，测试失败。

- [ ] **Step 3: 实施 Tool 私有存储和只读 property**

在 `Tool.__init__()` 中写入 `_name`、`_description`、`_permission_level`、`_parameters_schema`、`_timeout_seconds`。定义无 setter 的 property：

```python
@property
def name(self) -> str:
    return self._name

@property
def parameters_schema(self) -> dict[str, Any]:
    return deepcopy(self._parameters_schema)
```

其余三个 metadata 字段同样只读。内部 schema 在构造时深拷贝一次，每次读取再深拷贝。

- [ ] **Step 4: 收紧 Tool function name 并测试**

先把既有 overlong 测试改为 65 字符并期望最多 64；新增非法字符参数化测试：空格、点、斜杠、非 ASCII。确认 RED 后，在 `base.py` 使用预编译正则 `^[A-Za-z0-9_-]+$` 校验规范化名称，最大长度设为 64。

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py -q
```

Expected after implementation: 全部通过。

- [ ] **Step 5: 写非 object 和不可 JSON 序列化 schema 失败测试**

在 `test_tool_validation.py` 增加：

```python
def test_validate_tool_schema_requires_object_root() -> None:
    with pytest.raises(ToolSchemaError, match="root must be an object"):
        validate_tool_schema({"type": "string"})


def test_validate_tool_schema_requires_json_serializable_values() -> None:
    with pytest.raises(ToolSchemaError, match="JSON serializable"):
        validate_tool_schema(
            {
                "type": "object",
                "properties": {"value": {"enum": [{"not-json"}] }},
            }
        )
```

在 `test_tool_registry.py` 增加注册非 object schema 后 Registry 仍为空的原子性断言。

- [ ] **Step 6: 运行 schema 边界测试并确认 RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_validation.py tests/test_tool_registry.py -q
```

Expected: 非 object schema 目前被接受，至少一个新增测试失败。

- [ ] **Step 7: 实施 schema 根类型和 JSON 编码校验**

`validate_tool_schema()` 先对 mapping 做深拷贝，再执行：

```python
try:
    json.dumps(plain_schema, allow_nan=False)
except (TypeError, ValueError) as exc:
    raise ToolSchemaError("Tool parameter schema must be JSON serializable") from exc

try:
    Draft202012Validator.check_schema(plain_schema)
except SchemaError as exc:
    raise ToolSchemaError("Invalid Tool parameter schema") from exc

if plain_schema.get("type") != "object":
    raise ToolSchemaError("Tool parameter schema root must be an object")
```

错误不得包含 schema 值。`validate_tool_arguments()` 继续使用 Tool property 返回的副本。

- [ ] **Step 8: 运行 Task 2 定向测试并确认 GREEN**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py tests/test_tool_registry.py tests/test_tool_validation.py -q
```

Expected: 全部通过，Registry 查找/顺序/导出 API 无回归。

---

### Task 3: Enforce AgentRun/Message consistency and reconcile docs

**Files:**
- Modify: `backend/app/models/message.py`
- Modify: `backend/app/models/agent_run.py`
- Create: `backend/alembic/versions/20260718_0003_agent_run_message_consistency.py`
- Modify: `backend/tests/test_agent_models.py`
- Modify: `backend/tests/test_agent_migrations.py`
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/10-tool-calling-design.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: Message/AgentRun ORM relationships、revision `20260717_0002`、现有删除审计行为。
- Produces: `uq_messages_id_conversation_id`；`fk_agent_runs_user_message_conversation_messages`；不一致旧数据 fail-closed 迁移；同步后的 M1/M2 文档状态。

- [ ] **Step 1: 写跨会话 AgentRun/Message 失败测试**

在 `test_agent_models.py` 增加：

```python
def test_agent_run_user_message_must_match_conversation(
    db: tuple[Session, Engine],
) -> None:
    session, _ = db
    first = Conversation()
    second = Conversation()
    message = Message(conversation=second, role="user", content="other")
    session.add_all([first, second])
    session.flush()
    session.add(
        AgentRun(
            conversation_id=first.id,
            user_message_id=message.id,
            goal="invalid cross-conversation run",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
```

- [ ] **Step 2: 运行模型测试并确认 RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_models.py::test_agent_run_user_message_must_match_conversation -q
```

Expected: FAIL，因为当前 commit 成功。

- [ ] **Step 3: 更新 ORM 复合约束与 relationship 同步列**

`Message.__table_args__` 增加：

```python
UniqueConstraint(
    "id",
    "conversation_id",
    name="uq_messages_id_conversation_id",
)
```

`AgentRun.__table_args__` 增加：

```python
ForeignKeyConstraint(
    ["user_message_id", "conversation_id"],
    ["messages.id", "messages.conversation_id"],
    name="fk_agent_runs_user_message_conversation_messages",
    ondelete="RESTRICT",
)
```

从 `user_message_id` 列移除单列 ForeignKey。`Message.agent_runs` 与 `AgentRun.user_message` 使用同时比较 ID/conversation 的 `primaryjoin`，但以 `foreign_keys`/`foreign()` 只将 `user_message_id` 标为 relationship 同步列，确保删除 Message 时 ORM 只清空可空的 message ID，不清空 `conversation_id`。保留并重跑已有 `test_deleting_user_message_preserves_agent_audit_rows`。

- [ ] **Step 4: 运行模型文件并确认 GREEN**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_models.py -q
```

Expected: 跨会话被拒绝，正常创建、级联和删除 Message 保留审计行全部通过；不得出现新的 SQLAlchemy relationship warning。

- [ ] **Step 5: 先更新迁移测试并确认 RED**

修改 `test_upgrade_head_creates_agent_persistence_schema`，断言：

```python
agent_foreign_keys[("user_message_id", "conversation_id")]["referred_columns"] == [
    "id",
    "conversation_id",
]
agent_foreign_keys[("user_message_id", "conversation_id")]["options"][
    "ondelete"
] == "RESTRICT"
```

并断言 Message unique constraints 包含 `uq_messages_id_conversation_id`。

新增旧 revision 不一致数据升级测试：先 `command.upgrade(config, "20260717_0002")`，用合成 UUID/时间分别构造跨会话 Message 关联与悬空 `user_message_id`；再断言 `command.upgrade(config, "head")` 抛出不包含用户内容的 `RuntimeError`。

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_migrations.py -q
```

Expected: FAIL，因为新 revision 尚不存在。

- [ ] **Step 6: 创建 additive migration `20260718_0003`**

Revision metadata：

```python
revision = "20260718_0003"
down_revision = "20260717_0002"
```

`upgrade()` 第一条查询：

```sql
SELECT 1
FROM agent_runs AS ar
LEFT JOIN messages AS m ON m.id = ar.user_message_id
WHERE ar.user_message_id IS NOT NULL
  AND (m.id IS NULL OR ar.conversation_id <> m.conversation_id)
LIMIT 1
```

若存在结果，抛出：

```python
RuntimeError(
    "Cannot enforce AgentRun message conversation integrity: "
    "inconsistent audit rows exist"
)
```

随后使用 `op.batch_alter_table("messages")` 创建 `uq_messages_id_conversation_id`；使用 `op.batch_alter_table("agent_runs")` 删除 `fk_agent_runs_user_message_id_messages` 并创建复合外键 `fk_agent_runs_user_message_conversation_messages`，`ondelete="RESTRICT"`。

`downgrade()` 先把 AgentRun 复合外键恢复为 `user_message_id -> messages.id ON DELETE SET NULL`，再移除 Message 复合唯一约束。

- [ ] **Step 7: 运行迁移定向测试并修正至 GREEN**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_agent_migrations.py tests/test_migrations.py -q
```

Expected: head 约束、旧数据 fail-closed、downgrade 到 Plan 1 全部通过。

- [ ] **Step 8: 更新事实文档**

- README/README_CN 的 Alembic schema 列表增加 `agent_runs`、`tool_calls`，注明新 revision 约束 AgentRun 的 user Message 必须属于同一 Conversation。
- `docs/10-tool-calling-design.md` 增加：凭据型名称拒绝清单类别；Windows junction/reparse point 作为 `symlink` 报告且不递归；Tool metadata 只读、schema 防御性复制；注册 schema 根必须为 object 且 JSON 可序列化。
- Plan 2 执行表把已经交付并由测试证明的 Tool abstraction、Registry、内置只读工具、参数校验、安全边界和文档项标为完成，并新增一段 2026-07-18 审计修复记录，不把 M3 或 Plan 3 bridge 标为完成。
- CHANGELOG 新增 `Unreleased` / `Fixed`，只记录本批次实际修复，不宣称 M3 已开始。

- [ ] **Step 9: 运行文档和 diff 自检**

Run:

```powershell
git diff --check
git status --short
```

使用本地链接检查脚本验证 Markdown 相对链接；搜索 tracked diff 中的 API key/token/private key 模式。Expected: 无坏链接、无真实 secret、无跨 Plan 文件。

- [ ] **Step 10: 运行完整后端与依赖验证**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: 所有测试通过；只允许已有 Starlette TestClient/httpx 弃用 warning；pip check 无 broken requirements。

- [ ] **Step 11: 运行完整前端验证**

Run:

```powershell
npm run typecheck
npm run test
npm run build
```

Working directory: `frontend/`。Expected: TypeScript、完整 Vitest、production build 全部通过。

- [ ] **Step 12: 用全新临时 SQLite 运行 Alembic 往返验证**

在系统临时目录创建唯一 SQLite，设置临时 `DATABASE_URL`，依次执行：

```powershell
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current --check-heads
..\.venv\Scripts\python.exe -m alembic check
..\.venv\Scripts\python.exe -m alembic downgrade 20260717_0002
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Expected: head 为 `20260718_0003`，无新 upgrade operations；验证后只删除本次创建且已校验位于系统临时目录的 SQLite。

- [ ] **Step 13: 运行 FastAPI 无 Provider smoke 与最终 self-review**

使用 `TestClient` 验证 health 200、OpenAPI 200、404 的 UUID `X-Request-ID`；不调用 chat/provider。随后检查：

- diff 只覆盖三个审计修复 Step；
- 没有 `web_fetch`、M3 Provider tools 或后续 Plan 能力；
- 无 secrets、用户数据库和 tracked 生成物；
- ORM 与 migration 命名、FK、唯一约束和 downgrade 一致；
- 每个审计发现都有 RED/GREEN 证据；
- README、中文 README、CHANGELOG、Tool design 和 Plan 2 状态一致。

最终只提供建议 commit message，例如：

```text
fix(plan2): remediate tool safety and audit integrity
```

不执行 commit。
