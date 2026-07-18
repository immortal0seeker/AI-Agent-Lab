# Plan 2 M2 list_dir Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete `P2-M2-S4` through `P2-M2-S6` with a safe, bounded, recursive `list_dir` Tool registered beside `read_file`.

**Architecture:** Add one focused builtin Tool that validates arguments through the existing Draft 2020-12 boundary, resolves one workspace-relative root, and performs deterministic bounded traversal in `asyncio.to_thread`. Reuse a public sensitive-name policy from `security.py`, return both line-oriented content and structured entries, and keep Registry initialization caller-owned.

**Tech Stack:** Python 3.11, `asyncio`, `os.scandir`, `pathlib`, Pydantic `ToolResult`, jsonschema-backed Tool validation, pytest 9.

## Global Constraints

- Scope is exactly `P2-M2-S4` through `P2-M2-S6`; do not implement or decide `P2-M2-S7`.
- `path` is required; `max_depth` is optional, defaults to 2, and is limited to 1 through 3 by default.
- `max_depth=1` lists direct children; `max_depth=2` includes one additional level.
- The default maximum returned entry count is 500 and must be configurable with a positive integer.
- Sensitive names are filtered before metadata collection or recursion; ordinary `.gitignore` remains visible.
- Discovered symbolic links may be reported but must never be recursively followed.
- Never read file contents, a real `.env`, credentials, private keys, the user SQLite database, or a real Provider.
- Do not add Provider tool calling, Agent Loop, services/APIs, frontend Agent views, persistence changes, Shell/file-writing tools, RAG, Memory, MCP, Voice, Vision, or Desktop.
- Do not stage, commit, push, or create tags; the user owns Git mutations.
- Do not use subagents unless the user explicitly changes the current restriction; execute this plan inline with `executing-plans`.

## File Map

- Create `backend/app/tools/builtin/list_dir.py`: Tool contract, bounded traversal, result formatting, and safe failures.
- Create `backend/tests/test_tool_list_dir.py`: successful behavior, limits, security, and filesystem error coverage.
- Modify `backend/app/tools/security.py`: expose one shared sensitive-component helper and include `__pycache__`.
- Modify `backend/app/tools/builtin/__init__.py`: export and register `ListDirTool` after `ReadFileTool`.
- Modify `backend/app/tools/__init__.py`: public exports for the builtin and shared helper.
- Modify `backend/tests/test_tool_read_file.py`: verify builtin registration now exposes both tools in stable order.
- Modify `README.md`, `README_CN.md`, `docs/00-project-overview.md`, `docs/01-architecture.md`, and `docs/10-tool-calling-design.md`: describe the implemented S4-S6 boundary.
- Modify `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`: mark only S4-S6 done and append the verified acceptance record.
- Do not modify `CHANGELOG.md`: it contains released `0.1.0` history only and has no Unreleased section.

---

### Task 1: P2-M2-S4 list_dir Contract And Successful Traversal

**Files:**
- Create: `backend/tests/test_tool_list_dir.py`
- Create: `backend/app/tools/builtin/list_dir.py`

**Interfaces:**
- Consumes: `Tool`, `ToolResult`, `validate_tool_arguments()`, `resolve_workspace_path()`, `validate_directory_depth()`.
- Produces: `DEFAULT_LIST_DIR_DEPTH = 2`, `DEFAULT_MAX_LIST_ENTRIES = 500`, and `ListDirTool(workspace_root: Path, max_depth: int, max_entries: int)`.

- [ ] **Step 1: Write the S4 failing tests**

Create `backend/tests/test_tool_list_dir.py` with:

```python
import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.tools.builtin.list_dir import (
    DEFAULT_LIST_DIR_DEPTH,
    DEFAULT_MAX_LIST_ENTRIES,
    ListDirTool,
)


def run_tool(tool: ListDirTool, arguments: dict[str, Any]):
    return asyncio.run(tool.run(arguments))


def test_list_dir_declares_stable_tool_metadata(tmp_path: Path) -> None:
    tool = ListDirTool(workspace_root=tmp_path)

    assert tool.name == "list_dir"
    assert tool.description == "List files and directories in the workspace"
    assert tool.permission_level == "read_only"
    assert tool.parameters_schema == {
        "type": "object",
        "properties": {
            "path": {"type": "string", "minLength": 1},
            "max_depth": {
                "type": "integer",
                "minimum": 1,
                "maximum": 3,
                "default": 2,
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    }
    assert tool.default_depth == DEFAULT_LIST_DIR_DEPTH
    assert tool.max_entries == DEFAULT_MAX_LIST_ENTRIES


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("max_depth", 0),
        ("max_depth", 4),
        ("max_depth", True),
        ("max_depth", "3"),
        ("max_entries", 0),
        ("max_entries", True),
    ],
)
def test_list_dir_rejects_invalid_limits(
    tmp_path: Path,
    field_name: str,
    value: object,
) -> None:
    overrides: dict[str, object] = {
        "workspace_root": tmp_path,
        field_name: value,
    }

    with pytest.raises((TypeError, ValueError), match=field_name):
        ListDirTool(**overrides)  # type: ignore[arg-type]


def test_list_dir_returns_stable_names_types_sizes_and_default_depth(
    tmp_path: Path,
) -> None:
    alpha = tmp_path / "alpha"
    nested = alpha / "nested"
    nested.mkdir(parents=True)
    (alpha / "direct.txt").write_text("x", encoding="utf-8")
    (nested / "deep.txt").write_text("deep", encoding="utf-8")
    (tmp_path / "root.txt").write_text("root", encoding="utf-8")

    result = run_tool(ListDirTool(workspace_root=tmp_path), {"path": "."})

    assert result.success is True
    assert result.error is None
    assert result.data == {
        "entries": [
            {"path": "alpha", "name": "alpha", "type": "directory", "size_bytes": None},
            {"path": "alpha/direct.txt", "name": "direct.txt", "type": "file", "size_bytes": 1},
            {"path": "alpha/nested", "name": "nested", "type": "directory", "size_bytes": None},
            {"path": "root.txt", "name": "root.txt", "type": "file", "size_bytes": 4},
        ]
    }
    assert result.content == (
        "alpha\tdirectory\t-\n"
        "alpha/direct.txt\tfile\t1\n"
        "alpha/nested\tdirectory\t-\n"
        "root.txt\tfile\t4"
    )
    assert result.metadata == {
        "path": ".",
        "max_depth": 2,
        "entry_count": 4,
        "truncated": False,
    }


def test_list_dir_applies_explicit_depth_semantics(tmp_path: Path) -> None:
    nested = tmp_path / "level1" / "level2"
    nested.mkdir(parents=True)
    (nested / "level3.txt").write_text("x", encoding="utf-8")
    tool = ListDirTool(workspace_root=tmp_path)

    shallow = run_tool(tool, {"path": ".", "max_depth": 1})
    deep = run_tool(tool, {"path": ".", "max_depth": 3})

    assert [entry["path"] for entry in shallow.data["entries"]] == ["level1"]
    assert [entry["path"] for entry in deep.data["entries"]] == [
        "level1",
        "level1/level2",
        "level1/level2/level3.txt",
    ]


def test_list_dir_returns_success_for_empty_directory(tmp_path: Path) -> None:
    result = run_tool(ListDirTool(workspace_root=tmp_path), {"path": "."})

    assert result.success is True
    assert result.content == ""
    assert result.data == {"entries": []}
    assert result.metadata["entry_count"] == 0
    assert result.metadata["truncated"] is False


def test_list_dir_truncates_at_stable_entry_limit(tmp_path: Path) -> None:
    for name in ["c.txt", "a.txt", "b.txt"]:
        (tmp_path / name).write_text(name, encoding="utf-8")

    result = run_tool(
        ListDirTool(workspace_root=tmp_path, max_entries=2),
        {"path": "."},
    )

    assert result.success is True
    assert [entry["path"] for entry in result.data["entries"]] == [
        "a.txt",
        "b.txt",
    ]
    assert result.metadata["entry_count"] == 2
    assert result.metadata["truncated"] is True
```

- [ ] **Step 2: Run the focused test to verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_list_dir.py -q
```

Expected: collection fails because `app.tools.builtin.list_dir` does not exist.

- [ ] **Step 3: Implement the minimal bounded traversal**

Create `backend/app/tools/builtin/list_dir.py` with:

```python
from __future__ import annotations

import asyncio
import os
import stat
from pathlib import Path
from typing import Any

from app.tools.base import Tool, ToolResult
from app.tools.security import (
    DEFAULT_MAX_DIRECTORY_DEPTH,
    PROJECT_WORKSPACE_ROOT,
    ToolLimitError,
    ToolSecurityError,
    resolve_workspace_path,
    validate_directory_depth,
)
from app.tools.validation import (
    ToolArgumentValidationError,
    validate_tool_arguments,
)


DEFAULT_LIST_DIR_DEPTH = 2
DEFAULT_MAX_LIST_ENTRIES = 500

_INVALID_ARGUMENTS_ERROR = "Invalid list_dir arguments"
_UNSAFE_PATH_ERROR = "The requested path is not allowed"
_NOT_FOUND_ERROR = "The requested directory was not found"
_NOT_DIRECTORY_ERROR = "The requested path is not a directory"
_LIST_ERROR = "The requested directory could not be listed"


def _require_positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return value


class ListDirTool(Tool):
    def __init__(
        self,
        *,
        workspace_root: Path = PROJECT_WORKSPACE_ROOT,
        max_depth: int = DEFAULT_MAX_DIRECTORY_DEPTH,
        max_entries: int = DEFAULT_MAX_LIST_ENTRIES,
    ) -> None:
        if not isinstance(workspace_root, Path):
            raise TypeError("workspace_root must be a Path")
        configured_depth = _require_positive_int(max_depth, "max_depth")
        try:
            validate_directory_depth(configured_depth)
        except ToolLimitError as exc:
            raise ValueError(
                f"max_depth must not exceed {DEFAULT_MAX_DIRECTORY_DEPTH}"
            ) from exc
        configured_entries = _require_positive_int(max_entries, "max_entries")
        default_depth = min(DEFAULT_LIST_DIR_DEPTH, configured_depth)

        super().__init__(
            name="list_dir",
            description="List files and directories in the workspace",
            parameters_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": configured_depth,
                        "default": default_depth,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            permission_level="read_only",
        )
        self.workspace_root = workspace_root.resolve()
        self.max_depth = configured_depth
        self.default_depth = default_depth
        self.max_entries = configured_entries

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            validated = validate_tool_arguments(self, arguments)
        except ToolArgumentValidationError:
            return self._failure(_INVALID_ARGUMENTS_ERROR)
        requested_depth = validated.get("max_depth", self.default_depth)
        return await asyncio.to_thread(
            self._list_dir,
            validated["path"],
            requested_depth,
        )

    def _list_dir(self, path: str, max_depth: int) -> ToolResult:
        try:
            resolved = resolve_workspace_path(
                path,
                workspace_root=self.workspace_root,
            )
        except ToolSecurityError:
            return self._failure(_UNSAFE_PATH_ERROR)
        except OSError:
            return self._failure(_LIST_ERROR)

        try:
            directory_stat = resolved.stat()
        except FileNotFoundError:
            return self._failure(_NOT_FOUND_ERROR)
        except OSError:
            return self._failure(_LIST_ERROR)

        if not stat.S_ISDIR(directory_stat.st_mode):
            return self._failure(_NOT_DIRECTORY_ERROR)

        entries: list[dict[str, str | int | None]] = []
        try:
            truncated = self._walk_directory(
                resolved,
                current_depth=1,
                max_depth=max_depth,
                entries=entries,
            )
        except FileNotFoundError:
            return self._failure(_NOT_FOUND_ERROR)
        except OSError:
            return self._failure(_LIST_ERROR)

        entries.sort(
            key=lambda entry: (
                str(entry["path"]).casefold(),
                str(entry["path"]),
            )
        )
        relative_root = resolved.relative_to(self.workspace_root).as_posix()
        content = "\n".join(
            "\t".join(
                (
                    str(entry["path"]),
                    str(entry["type"]),
                    "-" if entry["size_bytes"] is None else str(entry["size_bytes"]),
                )
            )
            for entry in entries
        )
        return ToolResult(
            tool_name=self.name,
            success=True,
            content=content,
            data={"entries": entries},
            metadata={
                "path": relative_root,
                "max_depth": max_depth,
                "entry_count": len(entries),
                "truncated": truncated,
            },
        )

    def _walk_directory(
        self,
        directory: Path,
        *,
        current_depth: int,
        max_depth: int,
        entries: list[dict[str, str | int | None]],
    ) -> bool:
        with os.scandir(directory) as iterator:
            children = sorted(
                iterator,
                key=lambda entry: (entry.name.casefold(), entry.name),
            )

        for child in children:
            if child.is_symlink():
                entry_type = "symlink"
                size_bytes = None
            elif child.is_dir(follow_symlinks=False):
                entry_type = "directory"
                size_bytes = None
            elif child.is_file(follow_symlinks=False):
                entry_type = "file"
                size_bytes = child.stat(follow_symlinks=False).st_size
            else:
                continue

            child_path = Path(child.path)
            relative_path = child_path.relative_to(self.workspace_root).as_posix()
            entries.append(
                {
                    "path": relative_path,
                    "name": child.name,
                    "type": entry_type,
                    "size_bytes": size_bytes,
                }
            )
            if len(entries) >= self.max_entries:
                return True
            if entry_type == "directory" and current_depth < max_depth:
                if self._walk_directory(
                    child_path,
                    current_depth=current_depth + 1,
                    max_depth=max_depth,
                    entries=entries,
                ):
                    return True
        return False

    def _failure(self, error: str) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=False,
            error=error,
        )
```

- [ ] **Step 4: Run the S4 tests to verify GREEN**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_list_dir.py -q
```

Expected: `11 passed`.

- [ ] **Step 5: Inspect the S4 diff without Git mutation**

Run from the repository root:

```powershell
git diff -- backend/app/tools/builtin/list_dir.py backend/tests/test_tool_list_dir.py
git diff --check
```

Expected: only the new S4 Tool and tests appear; diff check prints no errors.

---

### Task 2: P2-M2-S5 Security And Error Handling

**Files:**
- Modify: `backend/tests/test_tool_list_dir.py`
- Modify: `backend/app/tools/security.py`
- Modify: `backend/app/tools/builtin/list_dir.py`

**Interfaces:**
- Consumes: Task 1 `ListDirTool` and existing `resolve_workspace_path()`.
- Produces: `is_sensitive_path_component(component: str) -> bool` shared by path resolution and traversal.

- [ ] **Step 1: Append the S5 failing tests**

Add `import os` to `backend/tests/test_tool_list_dir.py`, then append:

```python
@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"path": 42},
        {"path": ".", "max_depth": 0},
        {"path": ".", "max_depth": 4},
        {"path": ".", "secret_extra": "do-not-leak"},
    ],
)
def test_list_dir_returns_safe_failure_for_invalid_arguments(
    tmp_path: Path,
    arguments: dict[str, Any],
) -> None:
    result = run_tool(ListDirTool(workspace_root=tmp_path), arguments)

    assert result.success is False
    assert result.error == "Invalid list_dir arguments"
    assert "do-not-leak" not in result.model_dump_json()


@pytest.mark.parametrize(
    "path",
    ["../outside", ".env", ".git", "docs-local"],
)
def test_list_dir_rejects_unsafe_roots_without_echoing_them(
    tmp_path: Path,
    path: str,
) -> None:
    result = run_tool(ListDirTool(workspace_root=tmp_path), {"path": path})

    assert result.success is False
    assert result.error == "The requested path is not allowed"
    assert path not in result.model_dump_json()


def test_list_dir_filters_sensitive_entries_before_traversal(tmp_path: Path) -> None:
    for name in [".git", ".ssh", "docs-local", "__pycache__"]:
        directory = tmp_path / name
        directory.mkdir()
        (directory / "hidden.txt").write_text("secret", encoding="utf-8")
    for name in [".env", ".env.local", "id_rsa", "private.pem", "private.key"]:
        (tmp_path / name).write_text("secret", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("dist/", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("safe", encoding="utf-8")

    result = run_tool(
        ListDirTool(workspace_root=tmp_path),
        {"path": ".", "max_depth": 3},
    )

    assert result.success is True
    assert [entry["path"] for entry in result.data["entries"]] == [
        ".gitignore",
        "visible.txt",
    ]
    serialized = result.model_dump_json()
    assert "hidden.txt" not in serialized
    assert "secret" not in serialized


def test_list_dir_reports_but_never_follows_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "inside.txt").write_text("safe", encoding="utf-8")
    link = tmp_path / "linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("symbolic links are unavailable in this environment")

    result = run_tool(
        ListDirTool(workspace_root=tmp_path),
        {"path": ".", "max_depth": 3},
    )

    linked = next(
        entry for entry in result.data["entries"] if entry["path"] == "linked"
    )
    assert linked["type"] == "symlink"
    assert "linked/inside.txt" not in {
        entry["path"] for entry in result.data["entries"]
    }


def test_list_dir_returns_safe_failure_for_missing_directory(tmp_path: Path) -> None:
    result = run_tool(
        ListDirTool(workspace_root=tmp_path),
        {"path": "missing"},
    )

    assert result.success is False
    assert result.error == "The requested directory was not found"


def test_list_dir_rejects_regular_file(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("safe", encoding="utf-8")

    result = run_tool(
        ListDirTool(workspace_root=tmp_path),
        {"path": "file.txt"},
    )

    assert result.success is False
    assert result.error == "The requested path is not a directory"


def test_list_dir_returns_safe_failure_for_permission_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_listing(_: Path):
        raise PermissionError("credential-value")

    monkeypatch.setattr(os, "scandir", deny_listing)
    result = run_tool(ListDirTool(workspace_root=tmp_path), {"path": "."})

    assert result.success is False
    assert result.error == "The requested directory could not be listed"
    assert "credential-value" not in result.model_dump_json()
```

- [ ] **Step 2: Run S5 tests to verify RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_list_dir.py -q
```

Expected: the sensitive-entry test fails because Task 1 does not filter child names. Other failure-path tests may already pass and serve as regression coverage.

- [ ] **Step 3: Expose one shared sensitive-component policy**

In `backend/app/tools/security.py`, replace the directory-name constant and private helper with:

```python
_SENSITIVE_DIRECTORY_NAMES = frozenset(
    {".git", ".ssh", "__pycache__", "docs-local"}
)
_PRIVATE_KEY_NAMES = frozenset({"id_dsa", "id_ecdsa", "id_ed25519", "id_rsa"})


def is_sensitive_path_component(component: str) -> bool:
    if not isinstance(component, str):
        raise TypeError("component must be a string")
    normalized = _normalize_windows_component(component).casefold()
    return (
        normalized in _SENSITIVE_DIRECTORY_NAMES
        or normalized == ".env"
        or normalized.startswith(".env.")
        or normalized in _PRIVATE_KEY_NAMES
        or normalized.endswith((".pem", ".key"))
    )
```

In both checks inside `resolve_workspace_path()`, replace `_is_sensitive_component(...)` with `is_sensitive_path_component(...)`.

- [ ] **Step 4: Filter before metadata collection**

Add `is_sensitive_path_component` to the security imports in `backend/app/tools/builtin/list_dir.py`, then add this as the first statement inside `for child in children:`:

```python
            if is_sensitive_path_component(child.name):
                continue
```

This ordering is required: do not call `is_symlink()`, `is_dir()`, `is_file()`, or `stat()` for a sensitive child.

- [ ] **Step 5: Run focused and shared-security tests to verify GREEN**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_list_dir.py tests/test_tool_security.py -q
```

Expected: `58 passed` when symlink creation is available, or `57 passed, 1 skipped` when it is unavailable.

- [ ] **Step 6: Inspect the S5 diff without Git mutation**

Run from the repository root:

```powershell
git diff -- backend/app/tools/security.py backend/app/tools/builtin/list_dir.py backend/tests/test_tool_list_dir.py
git diff --check
```

Expected: the shared filter, list traversal guard, and S5 tests only; no raw exception text is returned.

---

### Task 3: P2-M2-S6 Builtin Registry Integration

**Files:**
- Modify: `backend/tests/test_tool_read_file.py`
- Modify: `backend/app/tools/builtin/__init__.py`
- Modify: `backend/app/tools/__init__.py`

**Interfaces:**
- Consumes: `ReadFileTool`, Task 2 `ListDirTool`, and caller-owned `ToolRegistry`.
- Produces: `register_builtin_tools()` registering `read_file` then `list_dir`, plus public imports for `ListDirTool` and its limits.

- [ ] **Step 1: Update registry tests to require both builtins**

In `backend/tests/test_tool_read_file.py`, add these imports:

```python
from app.tools.builtin.list_dir import ListDirTool
```

Replace `test_register_builtin_tools_adds_read_file_with_exportable_schema` with:

```python
def test_register_builtin_tools_adds_both_tools_with_exportable_schemas(
    tmp_path: Path,
) -> None:
    registry = ToolRegistry()

    register_builtin_tools(
        registry,
        workspace_root=tmp_path,
        max_file_bytes=123,
        max_characters=45,
        max_directory_depth=1,
        max_directory_entries=7,
    )

    read_file = registry.get_tool("read_file")
    list_dir = registry.get_tool("list_dir")
    assert isinstance(read_file, ReadFileTool)
    assert read_file.workspace_root == tmp_path.resolve()
    assert read_file.max_file_bytes == 123
    assert read_file.max_characters == 45
    assert isinstance(list_dir, ListDirTool)
    assert list_dir.workspace_root == tmp_path.resolve()
    assert list_dir.max_depth == 1
    assert list_dir.default_depth == 1
    assert list_dir.max_entries == 7
    assert [registered.name for registered in registry.list_tools()] == [
        "read_file",
        "list_dir",
    ]
    schemas = registry.get_openai_tool_schemas()
    assert [schema["function"]["name"] for schema in schemas] == [
        "read_file",
        "list_dir",
    ]
    assert schemas[1] == {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories in the workspace",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "max_depth": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 1,
                        "default": 1,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    }
```

Strengthen `test_register_builtin_tools_preserves_duplicate_error` with a state assertion:

```python
def test_register_builtin_tools_preserves_duplicate_error(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry, workspace_root=tmp_path)

    with pytest.raises(DuplicateToolError, match="read_file"):
        register_builtin_tools(registry, workspace_root=tmp_path)

    assert [tool.name for tool in registry.list_tools()] == [
        "read_file",
        "list_dir",
    ]
```

- [ ] **Step 2: Run the builtin registration tests to verify RED**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_read_file.py -q
```

Expected: registration test fails because `register_builtin_tools()` does not accept list-dir configuration and does not register `list_dir`.

- [ ] **Step 3: Register and export ListDirTool**

Replace `backend/app/tools/builtin/__init__.py` with:

```python
from pathlib import Path

from app.tools.builtin.list_dir import (
    DEFAULT_MAX_LIST_ENTRIES,
    ListDirTool,
)
from app.tools.builtin.read_file import (
    DEFAULT_MAX_READ_CHARACTERS,
    ReadFileTool,
)
from app.tools.registry import ToolRegistry
from app.tools.security import (
    DEFAULT_MAX_DIRECTORY_DEPTH,
    DEFAULT_MAX_FILE_BYTES,
    PROJECT_WORKSPACE_ROOT,
)


def register_builtin_tools(
    registry: ToolRegistry,
    *,
    workspace_root: Path = PROJECT_WORKSPACE_ROOT,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_characters: int = DEFAULT_MAX_READ_CHARACTERS,
    max_directory_depth: int = DEFAULT_MAX_DIRECTORY_DEPTH,
    max_directory_entries: int = DEFAULT_MAX_LIST_ENTRIES,
) -> None:
    if not isinstance(registry, ToolRegistry):
        raise TypeError("registry must be a ToolRegistry")
    registry.register_tool(
        ReadFileTool(
            workspace_root=workspace_root,
            max_file_bytes=max_file_bytes,
            max_characters=max_characters,
        )
    )
    registry.register_tool(
        ListDirTool(
            workspace_root=workspace_root,
            max_depth=max_directory_depth,
            max_entries=max_directory_entries,
        )
    )


__all__ = [
    "DEFAULT_MAX_LIST_ENTRIES",
    "DEFAULT_MAX_READ_CHARACTERS",
    "ListDirTool",
    "ReadFileTool",
    "register_builtin_tools",
]
```

Update `backend/app/tools/__init__.py` imports so the builtin block is:

```python
from app.tools.builtin import (
    DEFAULT_MAX_LIST_ENTRIES,
    DEFAULT_MAX_READ_CHARACTERS,
    ListDirTool,
    ReadFileTool,
    register_builtin_tools,
)
```

Add `is_sensitive_path_component` to the security import block. Add these names to `__all__` in alphabetical context:

```python
    "DEFAULT_MAX_LIST_ENTRIES",
    "ListDirTool",
    "is_sensitive_path_component",
```

- [ ] **Step 4: Run S6 and complete Tool foundation tests to verify GREEN**

Run:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_read_file.py tests/test_tool_list_dir.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py tests/test_tool_registry.py tests/test_tool_schemas.py tests/test_tool_security.py tests/test_tool_validation.py tests/test_tool_read_file.py tests/test_tool_list_dir.py -q
```

Expected: builtin focused tests pass; complete Tool foundation reports `144 passed` when symlinks are available, or `143 passed, 1 skipped` otherwise.

- [ ] **Step 5: Inspect the S6 diff without Git mutation**

Run from the repository root:

```powershell
git diff -- backend/app/tools/__init__.py backend/app/tools/builtin/__init__.py backend/tests/test_tool_read_file.py
git diff --check
```

Expected: only dual-builtin registration, exports, and matching tests appear.

---

### Task 4: Documentation And S4-S6 Acceptance Record

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/10-tool-calling-design.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: verified Task 1-3 behavior and test evidence.
- Produces: truthful current-stage documentation and a traceable S4-S6 acceptance record.

- [ ] **Step 1: Update current-stage summaries**

In `README.md`, replace the current Plan 2 stage block with prose containing these exact facts:

```markdown
Current development stage: Plan 2 M2 `read_file` and `list_dir` are complete.
Completed Plan 2 scope: `P2-M1-S1` through `P2-M2-S6`.

The M1 foundation includes Tool and ToolResult contracts, ToolCall transport
schemas, an ordered Tool Registry, Draft 2020-12 argument validation, read-only
path policy, and AgentRun/ToolCall ORM models with an Alembic migration. The
builtin Registry now exposes `read_file` and `list_dir` in stable order.
`read_file` safely performs bounded UTF-8 reads. `list_dir` performs bounded,
deterministic workspace traversal with depth and entry limits, filters
sensitive entries, and never follows discovered symlinks. Expected failures
become safe ToolResults. Provider tool calling, an Agent Loop, Agent APIs, and
frontend Agent/ToolCall views are not yet implemented.

Next batch: `P2-M2-S7` only.
```

Apply the equivalent Chinese facts in `README_CN.md`, preserving the existing bilingual style and using `P2-M2-S7` as the next batch.

- [ ] **Step 2: Update architecture and Tool design documentation**

In `docs/00-project-overview.md` and `docs/01-architecture.md`:

- change the current stage to S4-S6 complete;
- add `tools/builtin/list_dir.py` beside `read_file.py` in the tree;
- describe default depth 2, hard depth 3, 500-entry limit, stable structured output, sensitive filtering, and non-followed discovered symlinks;
- retain the explicit absence of Provider tool calling, Agent Loop, Agent APIs, and frontend visualization.

In `docs/10-tool-calling-design.md`, replace the current-scope and data-flow sections with these facts:

```markdown
`P2-M2-S1` through `P2-M2-S6` provide two executable read-only builtins,
`read_file` and `list_dir`, plus caller-controlled Registry initialization. No
Agent service, API, or Provider currently invokes them.

Caller-owned Registry
-> ReadFileTool or ListDirTool
-> argument and workspace security validation
-> bounded read or directory traversal
-> ToolResult
```

Add a dedicated `Built-in list_dir` section defining its arguments, depth semantics, 500-entry bound, entry fields, sensitive filters, symlink policy, safe errors, and `asyncio.to_thread` behavior. Remove `list_dir` from Deferred Work, while leaving optional `web_fetch` evaluation deferred.

- [ ] **Step 3: Mark only S4-S6 done and append the acceptance record**

In `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`, change only rows S4-S6 from `Codex` to `Codex（done）`. Keep S7 unchanged.

Immediately after the S1-S3 acceptance record, append a dated `P2-M2-S4～S6 list_dir 验收记录（2026-07-18）` table with these rows:

```markdown
| 验收项 | 结果与证据 |
|---|---|
| list_dir 契约 | 异步只读 `ListDirTool` 接受必填 `path` 和可选 `max_depth`；默认深度 2、硬上限 3、默认最多 500 条。成功结果同时返回逐行 `content`、结构化 `data.entries` 以及根路径、深度、条目数和截断状态 metadata。 |
| 遍历与安全 | 工作区相对路径复用 M1 sandbox；条目按规范化相对路径稳定排序，文件返回字节大小，目录返回空大小。敏感名称在 metadata 读取和递归前过滤；普通 `.gitignore` 可见；符号链接只报告、不跟随；所有文件系统工作进入 `asyncio.to_thread`。 |
| 异常处理 | 参数错误、越界/敏感根路径、缺失路径、非目录和权限/文件系统异常均返回固定失败 ToolResult，不回显参数、绝对路径、目录内容或原始异常。测试只使用临时工作区，未读取真实 secret、Provider 配置或用户数据库。 |
| Registry | `register_builtin_tools()` 由调用方持有并按 `read_file`、`list_dir` 顺序注册，支持注入两类 Tool 的限制并导出 OpenAI-compatible schemas；无 singleton、import-time 或应用启动副作用。 |
| TDD 与全量验证 | 记录实际 RED 原因、聚焦测试结果、Tool foundation、完整 backend pytest、`pip check`、frontend typecheck/Vitest/build 和文档/秘密/diff 检查的原始计数。 |
| Codex review 与边界 | 记录必须修问题及复验结论；确认未实现 S7、Provider tools、Agent Loop、service/API/frontend、RAG、Memory、MCP、Shell 或写文件能力，并说明是否需要 Claude Code 二次复审。 |
```

When filling the TDD and review rows, replace the descriptive instruction with the literal command results observed in Tasks 1-3 and Task 5; never invent a count or external review.

- [ ] **Step 4: Check documentation truth and links**

Run from the repository root:

```powershell
$files = @('README.md','README_CN.md','docs/00-project-overview.md','docs/01-architecture.md','docs/10-tool-calling-design.md','docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md')
Select-String -Path $files -Pattern 'P2-M2-S6|list_dir|P2-M2-S7|Provider tool calling|Agent Loop' -Encoding utf8
git diff --check
```

Expected: all six documents identify S4-S6 as complete, S7 as next/deferred, and later capabilities as unimplemented; diff check prints no errors.

---

### Task 5: Full Verification And Codex Self-Review

**Files:**
- Modify if evidence changed: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`

**Interfaces:**
- Consumes: all S4-S6 code, tests, and documentation.
- Produces: fresh completion evidence and a reviewed user-ready diff.

- [ ] **Step 1: Load the verification skill before completion claims**

Read `verification-before-completion/SKILL.md` completely and follow its evidence rules. Do not claim success based on Task 1-4 output alone.

- [ ] **Step 2: Run focused and complete backend verification**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_list_dir.py -q
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py tests/test_tool_registry.py tests/test_tool_schemas.py tests/test_tool_security.py tests/test_tool_validation.py tests/test_tool_read_file.py tests/test_tool_list_dir.py -q
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected before review additions: list-dir focused `25 passed` (or `24 passed, 1 skipped`), Tool foundation `144 passed` (or `143 passed, 1 skipped`), backend `269 passed, 1 warning` (or `268 passed, 1 skipped, 1 warning`), and `No broken requirements found.` The one expected warning remains the known Starlette TestClient/httpx deprecation warning; investigate any other warning or failure.

- [ ] **Step 3: Run complete frontend regression verification**

Run from `frontend/`:

```powershell
npm run typecheck
npm run test
npm run build
```

Expected: typecheck succeeds, 8 files / 37 tests pass, and the production build succeeds. If the managed sandbox blocks `dist` replacement with EPERM, rerun only `npm run build` using the already approved build escalation; do not alter source code to work around sandbox permissions.

- [ ] **Step 4: Run documentation, secret, artifact, and Git checks**

Run from the repository root without reading ignored secret files:

```powershell
$changed = @(
  git -c core.quotepath=false diff --name-only
  git -c core.quotepath=false ls-files --others --exclude-standard
) | Sort-Object -Unique
$changed
git diff --check
git diff --cached --check
git status --short --untracked-files=all
Select-String -Path $changed -Pattern 'sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,}|BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY' -Encoding utf8
git ls-files '*.pyc' '*.pyo'
git status --short --untracked-files=all -- '*.pyc' '*.pyo'
```

Expected: only S4-S6 code/tests/docs plus the approved spec/plan are changed; both diff checks print no errors; secret scan prints no matches; no Python artifact is tracked or Git-visible. Ignored runtime caches created by pytest may exist and must not be treated as source changes. Do not open `.env`, private keys, ignored SQLite files, SSH paths, browser profiles, or credentials.

- [ ] **Step 5: Run Codex self-review and classify findings**

Review the complete diff against the spec and execution table:

```powershell
git diff --stat
git diff -- backend/app/tools backend/tests/test_tool_list_dir.py backend/tests/test_tool_read_file.py README.md README_CN.md docs/00-project-overview.md docs/01-architecture.md docs/10-tool-calling-design.md 'docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md'
```

Check every item explicitly:

- traversal stops at depth and return-count limits;
- sensitive entries are filtered before metadata access;
- discovered symlinks are not followed;
- safe failures contain no raw arguments, absolute paths, directory data, or exception text;
- Registry order is `read_file`, `list_dir` with no global side effect;
- docs do not claim S7 or later Plan 2 capabilities;
- no Provider, Agent Loop, service/API/frontend, migration, RAG, Memory, MCP, Shell, write, or delete capability appears;
- no real secret, user database, external Provider, stage, commit, push, or tag operation occurred.

Classify each finding as must fix, fix in a later batch, record as limitation, or not applicable. For every must-fix item, add a focused failing regression test, run it RED, implement the smallest fix, and rerun focused plus complete verification.

- [ ] **Step 6: Finalize acceptance evidence and recheck the final diff**

Update the execution-table TDD/review rows with the literal final command counts and any review fix. Then rerun:

```powershell
git diff --check
git status --short --untracked-files=all
```

Expected: no diff errors; all changes remain limited to S4-S6 and its approved planning/acceptance documentation.

Do not commit. Hand off a concise summary, verification evidence, Codex review conclusion, Claude Code review recommendation, residual limitations, next-step suggestion limited to `P2-M2-S7`, and suggested manual commit message:

```text
feat(tools): add safe list directory builtin
```
