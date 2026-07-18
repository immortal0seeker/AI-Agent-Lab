# Plan 2 M2 Read File Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and register a safe, bounded, UTF-8-only `read_file` Tool for `P2-M2-S1` through `P2-M2-S3`.

**Architecture:** `ReadFileTool` reuses the existing Tool, validation, and workspace-path security contracts, performs bounded file I/O in `asyncio.to_thread`, and converts expected user/security/filesystem failures into safe `ToolResult` errors. A caller-controlled `register_builtin_tools()` function adds the Tool to an existing `ToolRegistry` without global state or application startup integration.

**Tech Stack:** Python 3.11, asyncio, pathlib, Pydantic ToolResult, JSON Schema Draft 2020-12 validation, pytest.

## Global Constraints

- Work only on `P2-M2-S1` through `P2-M2-S3`.
- Do not implement `list_dir`, `web_fetch`, Provider tool calling, Agent Loop, Agent services/APIs, frontend Agent views, RAG, Memory, MCP, Shell Tool, or file-writing tools.
- Accept only UTF-8 and UTF-8 BOM text; reject NUL-bearing and non-UTF-8 content.
- Keep the existing default byte limit of `1_048_576` bytes and use a default returned-character limit of `100_000`.
- Oversized byte content fails; overlong decoded text succeeds with truncation metadata.
- Expected failures must not expose argument values, file contents, absolute paths, or raw exception text.
- Tests may read only fake `tmp_path` content and the tracked repository `README.md`; never read a real `.env`, credential, private key, user database, or sensitive local path.
- Do not call a real Provider or external service.
- Do not modify `CHANGELOG.md`; `v0.1.0` remains the current release.
- The user creates the final commit manually; do not stage, commit, push, or create a tag.

---

### Task 1: ReadFileTool Contract and Successful Reads

**Files:**
- Create: `backend/app/tools/builtin/read_file.py`
- Create: `backend/tests/test_tool_read_file.py`

**Interfaces:**
- Consumes: `Tool`, `ToolResult`, `resolve_workspace_path()`, `validate_file_size()`, and `validate_tool_arguments()`.
- Produces: `DEFAULT_MAX_READ_CHARACTERS: int = 100_000`.
- Produces: `ReadFileTool(*, workspace_root: Path = PROJECT_WORKSPACE_ROOT, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES, max_characters: int = DEFAULT_MAX_READ_CHARACTERS)`.
- Produces: asynchronous `ReadFileTool.run(arguments: dict[str, Any]) -> ToolResult`.

- [ ] **Step 1: Verify the committed baseline before feature code**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: `217 passed, 1 warning`; the warning is the accepted Starlette
TestClient/httpx deprecation warning; dependency consistency is clean.

- [ ] **Step 2: Write failing successful-read and constructor tests**

Create `backend/tests/test_tool_read_file.py`:

```python
import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.tools.builtin.read_file import (
    DEFAULT_MAX_READ_CHARACTERS,
    ReadFileTool,
)


def run_tool(tool: ReadFileTool, arguments: dict[str, Any]):
    return asyncio.run(tool.run(arguments))


def test_read_file_declares_stable_tool_metadata(tmp_path: Path) -> None:
    tool = ReadFileTool(workspace_root=tmp_path)

    assert tool.name == "read_file"
    assert tool.description == "Read a UTF-8 text file from the workspace"
    assert tool.permission_level == "read_only"
    assert tool.parameters_schema == {
        "type": "object",
        "properties": {
            "path": {"type": "string", "minLength": 1},
        },
        "required": ["path"],
        "additionalProperties": False,
    }
    assert tool.max_characters == DEFAULT_MAX_READ_CHARACTERS


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("max_file_bytes", 0),
        ("max_file_bytes", True),
        ("max_file_bytes", "1"),
        ("max_characters", -1),
        ("max_characters", True),
        ("max_characters", "1"),
    ],
)
def test_read_file_rejects_invalid_limits(
    tmp_path: Path,
    field_name: str,
    value: object,
) -> None:
    overrides: dict[str, object] = {
        "workspace_root": tmp_path,
        field_name: value,
    }

    with pytest.raises((TypeError, ValueError), match=field_name):
        ReadFileTool(**overrides)  # type: ignore[arg-type]


def test_read_file_reads_utf8_text_and_returns_metadata(tmp_path: Path) -> None:
    content = "# Guide\n你好，workspace\n"
    raw = content.encode("utf-8")
    (tmp_path / "README.md").write_bytes(raw)

    result = run_tool(ReadFileTool(workspace_root=tmp_path), {"path": "README.md"})

    assert result.success is True
    assert result.content == content
    assert result.error is None
    assert result.metadata == {
        "path": "README.md",
        "encoding": "utf-8",
        "size_bytes": len(raw),
        "character_count": len(content),
        "returned_characters": len(content),
        "truncated": False,
    }


def test_read_file_accepts_utf8_bom_without_returning_the_bom(tmp_path: Path) -> None:
    text = "BOM text"
    raw = b"\xef\xbb\xbf" + text.encode("utf-8")
    (tmp_path / "bom.txt").write_bytes(raw)

    result = run_tool(ReadFileTool(workspace_root=tmp_path), {"path": "bom.txt"})

    assert result.success is True
    assert result.content == text
    assert result.metadata["size_bytes"] == len(raw)
    assert result.metadata["character_count"] == len(text)


def test_read_file_truncates_by_character_with_explicit_metadata(
    tmp_path: Path,
) -> None:
    (tmp_path / "long.txt").write_text("abcdef", encoding="utf-8")
    tool = ReadFileTool(workspace_root=tmp_path, max_characters=4)

    result = run_tool(tool, {"path": "long.txt"})

    assert result.success is True
    assert result.content == "abcd"
    assert result.metadata["character_count"] == 6
    assert result.metadata["returned_characters"] == 4
    assert result.metadata["truncated"] is True


def test_read_file_default_workspace_reads_tracked_readme() -> None:
    result = run_tool(ReadFileTool(), {"path": "README.md"})

    assert result.success is True
    assert result.content.startswith("# AI Agent Lab")
    assert result.metadata["path"] == "README.md"
```

- [ ] **Step 3: Run Task 1 tests to verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_read_file.py -q
```

Expected: collection fails because `app.tools.builtin.read_file` does not
exist. This is the S1 RED evidence.

- [ ] **Step 4: Implement the minimal successful-read path**

Create `backend/app/tools/builtin/read_file.py`:

```python
from __future__ import annotations

import asyncio
import stat
from pathlib import Path
from typing import Any

from app.tools.base import Tool, ToolResult
from app.tools.security import (
    DEFAULT_MAX_FILE_BYTES,
    PROJECT_WORKSPACE_ROOT,
    resolve_workspace_path,
    validate_file_size,
)
from app.tools.validation import validate_tool_arguments


DEFAULT_MAX_READ_CHARACTERS = 100_000


def _require_positive_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return value


class ReadFileTool(Tool):
    def __init__(
        self,
        *,
        workspace_root: Path = PROJECT_WORKSPACE_ROOT,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_characters: int = DEFAULT_MAX_READ_CHARACTERS,
    ) -> None:
        super().__init__(
            name="read_file",
            description="Read a UTF-8 text file from the workspace",
            parameters_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            permission_level="read_only",
        )
        if not isinstance(workspace_root, Path):
            raise TypeError("workspace_root must be a Path")
        self.workspace_root = workspace_root.resolve()
        self.max_file_bytes = _require_positive_int(
            max_file_bytes,
            "max_file_bytes",
        )
        self.max_characters = _require_positive_int(
            max_characters,
            "max_characters",
        )

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        validated = validate_tool_arguments(self, arguments)
        return await asyncio.to_thread(self._read_file, validated["path"])

    def _read_file(self, path: str) -> ToolResult:
        resolved = resolve_workspace_path(
            path,
            workspace_root=self.workspace_root,
        )
        file_stat = resolved.stat()
        if not stat.S_ISREG(file_stat.st_mode):
            raise IsADirectoryError(path)
        validate_file_size(
            file_stat.st_size,
            max_file_bytes=self.max_file_bytes,
        )
        raw = resolved.read_bytes()
        validate_file_size(len(raw), max_file_bytes=self.max_file_bytes)
        text = raw.decode("utf-8-sig")
        content = text[: self.max_characters]
        relative_path = resolved.relative_to(self.workspace_root).as_posix()
        return ToolResult(
            tool_name=self.name,
            success=True,
            content=content,
            metadata={
                "path": relative_path,
                "encoding": "utf-8",
                "size_bytes": len(raw),
                "character_count": len(text),
                "returned_characters": len(content),
                "truncated": len(content) < len(text),
            },
        )
```

- [ ] **Step 5: Run Task 1 tests to verify GREEN**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_read_file.py -q
```

Expected: `11 passed`.

---

### Task 2: Safe Failures and Security Coverage

**Files:**
- Modify: `backend/app/tools/builtin/read_file.py`
- Modify: `backend/tests/test_tool_read_file.py`

**Interfaces:**
- Consumes: Task 1 `ReadFileTool` and M1 security/argument validation exceptions.
- Produces: expected invalid-input, security, size, encoding, and filesystem failures as safe `ToolResult(success=False)` values.
- Preserves: unexpected programmer/configuration errors remain exceptions.

- [ ] **Step 1: Append failing safe-error tests**

Append to `backend/tests/test_tool_read_file.py`:

```python
@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"path": 42},
        {"path": "README.md", "secret_extra": "do-not-leak"},
    ],
)
def test_read_file_returns_safe_failure_for_invalid_arguments(
    tmp_path: Path,
    arguments: dict[str, Any],
) -> None:
    result = run_tool(ReadFileTool(workspace_root=tmp_path), arguments)

    assert result.success is False
    assert result.error == "Invalid read_file arguments"
    assert "do-not-leak" not in result.model_dump_json()


@pytest.mark.parametrize("path", [".env", "../outside.txt", "id_rsa"])
def test_read_file_rejects_unsafe_paths_without_echoing_them(
    tmp_path: Path,
    path: str,
) -> None:
    result = run_tool(ReadFileTool(workspace_root=tmp_path), {"path": path})

    assert result.success is False
    assert result.error == "The requested path is not allowed"
    assert path not in result.model_dump_json()


def test_read_file_returns_safe_failure_for_missing_file(tmp_path: Path) -> None:
    result = run_tool(
        ReadFileTool(workspace_root=tmp_path),
        {"path": "missing.txt"},
    )

    assert result.success is False
    assert result.error == "The requested file was not found"


def test_read_file_rejects_directory(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()

    result = run_tool(ReadFileTool(workspace_root=tmp_path), {"path": "docs"})

    assert result.success is False
    assert result.error == "The requested path is not a regular file"


def test_read_file_rejects_oversized_file_before_reading(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "large.txt").write_bytes(b"x" * 11)

    def fail_if_read(_: Path) -> bytes:
        pytest.fail("oversized file content must not be read")

    monkeypatch.setattr(Path, "read_bytes", fail_if_read)
    result = run_tool(
        ReadFileTool(workspace_root=tmp_path, max_file_bytes=10),
        {"path": "large.txt"},
    )

    assert result.success is False
    assert result.error == "The requested file exceeds the size limit"


@pytest.mark.parametrize(
    "raw",
    [
        b"safe\x00hidden-value",
        b"\xffhidden-value",
    ],
)
def test_read_file_rejects_binary_or_non_utf8_without_content_leak(
    tmp_path: Path,
    raw: bytes,
) -> None:
    (tmp_path / "binary.dat").write_bytes(raw)

    result = run_tool(
        ReadFileTool(workspace_root=tmp_path),
        {"path": "binary.dat"},
    )

    assert result.success is False
    assert result.error == "The requested file is not supported UTF-8 text"
    assert "hidden-value" not in result.model_dump_json()


def test_read_file_returns_safe_failure_for_oserror(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "unreadable.txt").write_text("safe", encoding="utf-8")

    def raise_oserror(_: Path) -> bytes:
        raise OSError("credential-value")

    monkeypatch.setattr(Path, "read_bytes", raise_oserror)
    result = run_tool(
        ReadFileTool(workspace_root=tmp_path),
        {"path": "unreadable.txt"},
    )

    assert result.success is False
    assert result.error == "The requested file could not be read"
    assert "credential-value" not in result.model_dump_json()
```

- [ ] **Step 2: Run the expanded suite to verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_read_file.py -q
```

Expected: the original 11 tests pass and the 12 new cases fail because expected
errors are still raised or NUL content is still returned successfully.

- [ ] **Step 3: Convert only expected failures into safe ToolResult errors**

Add these imports and constants to `backend/app/tools/builtin/read_file.py`:

```python
from app.tools.security import (
    DEFAULT_MAX_FILE_BYTES,
    PROJECT_WORKSPACE_ROOT,
    ToolLimitError,
    ToolSecurityError,
    resolve_workspace_path,
    validate_file_size,
)
from app.tools.validation import (
    ToolArgumentValidationError,
    validate_tool_arguments,
)


_INVALID_ARGUMENTS_ERROR = "Invalid read_file arguments"
_UNSAFE_PATH_ERROR = "The requested path is not allowed"
_NOT_FOUND_ERROR = "The requested file was not found"
_NOT_FILE_ERROR = "The requested path is not a regular file"
_TOO_LARGE_ERROR = "The requested file exceeds the size limit"
_UNSUPPORTED_TEXT_ERROR = "The requested file is not supported UTF-8 text"
_READ_ERROR = "The requested file could not be read"
```

Replace `run()` and `_read_file()` and add `_failure()`:

```python
    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            validated = validate_tool_arguments(self, arguments)
        except ToolArgumentValidationError:
            return self._failure(_INVALID_ARGUMENTS_ERROR)
        return await asyncio.to_thread(self._read_file, validated["path"])

    def _read_file(self, path: str) -> ToolResult:
        try:
            resolved = resolve_workspace_path(
                path,
                workspace_root=self.workspace_root,
            )
        except ToolSecurityError:
            return self._failure(_UNSAFE_PATH_ERROR)
        except OSError:
            return self._failure(_READ_ERROR)

        try:
            file_stat = resolved.stat()
        except FileNotFoundError:
            return self._failure(_NOT_FOUND_ERROR)
        except OSError:
            return self._failure(_READ_ERROR)

        if not stat.S_ISREG(file_stat.st_mode):
            return self._failure(_NOT_FILE_ERROR)

        try:
            validate_file_size(
                file_stat.st_size,
                max_file_bytes=self.max_file_bytes,
            )
        except ToolLimitError:
            return self._failure(_TOO_LARGE_ERROR)

        try:
            raw = resolved.read_bytes()
        except FileNotFoundError:
            return self._failure(_NOT_FOUND_ERROR)
        except OSError:
            return self._failure(_READ_ERROR)

        try:
            validate_file_size(len(raw), max_file_bytes=self.max_file_bytes)
        except ToolLimitError:
            return self._failure(_TOO_LARGE_ERROR)

        if b"\x00" in raw:
            return self._failure(_UNSUPPORTED_TEXT_ERROR)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return self._failure(_UNSUPPORTED_TEXT_ERROR)

        content = text[: self.max_characters]
        relative_path = resolved.relative_to(self.workspace_root).as_posix()
        return ToolResult(
            tool_name=self.name,
            success=True,
            content=content,
            metadata={
                "path": relative_path,
                "encoding": "utf-8",
                "size_bytes": len(raw),
                "character_count": len(text),
                "returned_characters": len(content),
                "truncated": len(content) < len(text),
            },
        )

    def _failure(self, error: str) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=False,
            error=error,
        )
```

Do not catch `TypeError`, `ValueError`, or unexpected programmer errors outside
the explicitly listed validation, security, and filesystem cases.

- [ ] **Step 4: Run Task 2 tests to verify GREEN**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_read_file.py -q
```

Expected: `23 passed`.

---

### Task 3: Caller-Controlled Builtin Registration

**Files:**
- Create: `backend/app/tools/builtin/__init__.py`
- Modify: `backend/app/tools/__init__.py`
- Modify: `backend/tests/test_tool_read_file.py`

**Interfaces:**
- Consumes: `ReadFileTool` and caller-owned `ToolRegistry`.
- Produces: `register_builtin_tools(registry: ToolRegistry, *, workspace_root: Path = PROJECT_WORKSPACE_ROOT, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES, max_characters: int = DEFAULT_MAX_READ_CHARACTERS) -> None`.
- Exports: `DEFAULT_MAX_READ_CHARACTERS`, `ReadFileTool`, and `register_builtin_tools` from `app.tools`.

- [ ] **Step 1: Append failing registration tests**

Update imports in `backend/tests/test_tool_read_file.py`:

```python
from app.tools import (
    DuplicateToolError,
    ToolRegistry,
    register_builtin_tools,
)
```

Append:

```python
def test_register_builtin_tools_adds_read_file_with_exportable_schema(
    tmp_path: Path,
) -> None:
    registry = ToolRegistry()

    register_builtin_tools(
        registry,
        workspace_root=tmp_path,
        max_file_bytes=123,
        max_characters=45,
    )

    tool = registry.get_tool("read_file")
    assert isinstance(tool, ReadFileTool)
    assert tool.workspace_root == tmp_path.resolve()
    assert tool.max_file_bytes == 123
    assert tool.max_characters == 45
    assert [registered.name for registered in registry.list_tools()] == [
        "read_file"
    ]
    assert registry.get_openai_tool_schemas() == [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a UTF-8 text file from the workspace",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "minLength": 1},
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                },
            },
        }
    ]


def test_register_builtin_tools_preserves_duplicate_error(tmp_path: Path) -> None:
    registry = ToolRegistry()
    register_builtin_tools(registry, workspace_root=tmp_path)

    with pytest.raises(DuplicateToolError, match="read_file"):
        register_builtin_tools(registry, workspace_root=tmp_path)


def test_register_builtin_tools_rejects_non_registry(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="ToolRegistry"):
        register_builtin_tools(  # type: ignore[arg-type]
            object(),
            workspace_root=tmp_path,
        )
```

- [ ] **Step 2: Run registration tests to verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_read_file.py -q
```

Expected: collection fails because `register_builtin_tools` is not exported.

- [ ] **Step 3: Implement builtin initialization without global state**

Create `backend/app/tools/builtin/__init__.py`:

```python
from pathlib import Path

from app.tools.builtin.read_file import (
    DEFAULT_MAX_READ_CHARACTERS,
    ReadFileTool,
)
from app.tools.registry import ToolRegistry
from app.tools.security import DEFAULT_MAX_FILE_BYTES, PROJECT_WORKSPACE_ROOT


def register_builtin_tools(
    registry: ToolRegistry,
    *,
    workspace_root: Path = PROJECT_WORKSPACE_ROOT,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_characters: int = DEFAULT_MAX_READ_CHARACTERS,
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


__all__ = [
    "DEFAULT_MAX_READ_CHARACTERS",
    "ReadFileTool",
    "register_builtin_tools",
]
```

Add to `backend/app/tools/__init__.py` after the existing imports:

```python
from app.tools.builtin import (
    DEFAULT_MAX_READ_CHARACTERS,
    ReadFileTool,
    register_builtin_tools,
)
```

Add these names to `__all__` in alphabetical grouping with the existing names:

```python
    "DEFAULT_MAX_READ_CHARACTERS",
    "ReadFileTool",
    "register_builtin_tools",
```

- [ ] **Step 4: Run all read_file tests to verify GREEN**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_read_file.py -q
```

Expected: `26 passed`.

- [ ] **Step 5: Run the complete Tool foundation regression suite**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py tests/test_tool_registry.py tests/test_tool_schemas.py tests/test_tool_security.py tests/test_tool_validation.py tests/test_tool_read_file.py -q
```

Expected: `118 passed`.

---

### Task 4: Documentation, Review, and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Modify: `docs/00-project-overview.md`
- Modify: `docs/01-architecture.md`
- Modify: `docs/10-tool-calling-design.md`
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Keep unchanged: `CHANGELOG.md`

**Interfaces:**
- Consumes: the verified S1-S3 implementation and test evidence.
- Produces: accurate current-development scope, safety boundary, acceptance record, and next-batch pointer.

- [ ] **Step 1: Update current-stage and design documentation**

Update `README.md` and `README_CN.md` so they state:

```text
Current development stage: Plan 2 M2 read_file is complete.
Completed Plan 2 scope: P2-M1-S1 through P2-M2-S3.
Next batch: P2-M2-S4 through P2-M2-S6.
```

Describe only the implemented behavior: workspace-relative UTF-8 reads, safe
failure results, 1 MiB rejection, 100,000-character truncation metadata, and
caller-controlled Registry initialization. Continue to state that `list_dir`,
Provider tool calling, Agent Loop, API, and frontend integration do not exist.

Update `docs/01-architecture.md`:

- add `tools/builtin/read_file.py` to the repository structure;
- change the Tool Calling section from definitions-only to one executable
  read-only Tool with no Agent/Provider integration;
- document the validation/security/read/decode/truncate/result flow;
- document that expected failures become safe `ToolResult` errors.

Update `docs/00-project-overview.md` so its current stage, implemented read_file
summary, deferred boundary, and next batch match the README.

Update `docs/10-tool-calling-design.md`:

- change Current Scope to say M1 plus `P2-M2-S1` through `S3` are implemented;
- add a Built-in read_file section with its schema, limits, encoding, metadata,
  safe failures, and registration helper;
- remove `Built-in read-only tools` as a blanket deferred item and replace it
  with `list_dir and optional web_fetch evaluation`;
- retain Provider, Agent Loop, API, frontend, and Plan 4 deferrals.

Do not edit `CHANGELOG.md`.

- [ ] **Step 2: Run complete backend verification**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: `243 passed, 1 warning`; only the accepted Starlette
TestClient/httpx deprecation warning remains; dependencies are consistent.

- [ ] **Step 3: Run unchanged frontend verification**

Run from `frontend/`:

```powershell
npm run typecheck
npm run test
npm run build
```

Expected: typecheck passes, 8 files / 37 tests pass, and production build
transforms 1804 modules.

- [ ] **Step 4: Perform Codex review and classify every finding**

Review the full batch and confirm:

- the Tool parameter schema requires only `path` and rejects extras;
- constructor limits reject booleans, non-integers, zero, and negative values;
- expected invalid/security/filesystem cases return safe failed ToolResults;
- oversized files are rejected before `read_bytes()` and checked again after
  reading;
- UTF-8 BOM is removed, NUL/non-UTF-8 is rejected, and truncation is by decoded
  character rather than byte;
- successful metadata contains no absolute path;
- failure JSON contains no rejected content or raw exception;
- Registry initialization has no singleton/import-time registration;
- no `list_dir`, Provider tools, Agent Loop, service/API/frontend, RAG, Memory,
  MCP, shell, write, delete, or network capability was introduced;
- no real `.env`, secret, private key, user database, or Provider was accessed;
- `CHANGELOG.md` remains unchanged.

Classify findings as must fix, later batch, limitation, or not applicable. Fix
each must-fix issue with a failing regression test before repeating focused and
full verification. Claude Code is not required by the S1-S3 execution row and
must not be run unless the user explicitly requests it.

The completed review found one must-fix bounded-I/O gap: `Path.read_bytes()`
could allocate beyond the configured limit if a file grew after `stat`. Its RED
regression proved the old implementation called `read(-1)`; the fix uses
`open("rb").read(max_file_bytes + 1)`. The final focused counts therefore add
one test beyond the pre-review Task 3 checkpoint.

- [ ] **Step 5: Update the execution table with verified evidence**

Only after Steps 2-4 pass, update the Plan 2 execution table:

- mark Batch 4 `已完成`;
- mark `P2-M2-S1`, `S2`, and `S3` as `Codex（done）`;
- add a dated S1-S3 acceptance record containing the actual focused/full test,
  frontend, security, documentation, and review results;
- state that `P2-M2-S4` through `S6` is next and was not implemented;
- leave Batch 5 and every later Step unchanged.

Use these verified counts when all planned tests pass:

```text
read_file focused: 27 passed
complete Tool foundation: 119 passed
complete backend: 244 passed, 1 warning
frontend: 8 files / 37 tests, typecheck and build passed
```

- [ ] **Step 6: Run final documentation, secret, artifact, and diff checks**

From the repository root, verify:

```powershell
git status --short --untracked-files=all
git diff --check
git diff --cached --check
git diff --exit-code -- CHANGELOG.md
rg -n "list_dir|web_fetch|Agent Loop|Provider tools|RAG|Memory|MCP" backend/app/tools README.md README_CN.md docs/01-architecture.md docs/10-tool-calling-design.md
```

Also parse relative Markdown links in the changed README/docs files and verify
each target exists. Scan only the explicit changed files for common API-key,
private-key, token-assignment, `.env`, SQLite, `dist`, and cache artifact
patterns. Expected: no broken links, no secret-like value, no generated artifact,
no staged change, clean diff checks, and only documented mentions of deferred
capabilities.

- [ ] **Step 7: Prepare the manual-commit handoff**

Do not stage or commit. Report the complete changed-file list, verification
evidence, Codex review classification, residual limitations, and the next batch
`P2-M2-S4` through `P2-M2-S6`.

Suggested commit message:

```text
feat(tools): add safe read file builtin
```
