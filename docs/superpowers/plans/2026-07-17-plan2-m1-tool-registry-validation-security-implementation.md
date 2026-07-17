# Plan 2 M1 Tool Registry, Validation, and Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Repository instructions prohibit sub-agent execution for this batch.

**Goal:** Complete `P2-M1-S4` through `P2-M1-S6` with an in-memory Tool Registry, standards-based argument validation, and a read-only workspace security boundary.

**Architecture:** `app/tools/validation.py` validates Tool schemas and arguments with JSON Schema Draft 2020-12. `app/tools/registry.py` owns exact-name discovery and Provider-neutral OpenAI function-schema export, while `app/tools/security.py` owns pure path and resource-limit checks without filesystem reads.

**Tech Stack:** Python 3.11, Pydantic 2, pytest 9, `jsonschema>=4.26.0,<5.0.0`, and standard-library `pathlib`, `dataclasses`, `copy`, and `typing`.

## Global Constraints

- Work only on `P2-M1-S4` through `P2-M1-S6`.
- Do not implement S7 persistence, ORM models, migrations, built-in tools, Provider tool calling, Agent Loop, API routes, frontend behavior, RAG, Memory, MCP, Shell Tool, or file-writing tools.
- Do not read a real `.env`, user database, credentials, SSH keys, browser profiles, or system credential stores.
- Do not call a real or paid Provider; all Tool tests use in-process Mock Tool objects or `tmp_path`.
- Add `jsonschema>=4.26.0,<5.0.0` to both dependency manifests and install only that dependency into the existing project virtual environment.
- Use JSON Schema Draft 2020-12; do not silently add `additionalProperties: false` to Tool schemas.
- Resolve paths without opening or enumerating them; reject sensitive paths and workspace escapes before any future I/O.
- Add Chinese comments or docstrings only where they clarify a non-obvious boundary.
- Do not stage, commit, push, tag, or create a PR; the user commits the verified batch manually.

---

### Task 1: JSON Schema Dependency and Argument Validation

**Files:**
- Modify: `requirements.txt`
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/test_tool_validation.py`
- Create: `backend/app/tools/validation.py`
- Modify: `backend/app/tools/__init__.py`

**Interfaces:**
- Consumes: `Tool` and `ToolError` from `app.tools.base`.
- Produces: `ToolValidationIssue(path, code, message)`.
- Produces: `ToolSchemaError` and `ToolArgumentValidationError`.
- Produces: `validate_tool_schema(schema: Mapping[str, Any]) -> None`.
- Produces: `validate_tool_arguments(tool: Tool, arguments: Mapping[str, Any]) -> dict[str, Any]`.

- [ ] **Step 1: Add the direct dependency to both manifests**

Add this runtime dependency beside the other alphabetized backend dependencies
in `requirements.txt` and `backend/pyproject.toml`:

```text
jsonschema>=4.26.0,<5.0.0
```

- [ ] **Step 2: Install only the new dependency in the existing virtual environment**

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install "jsonschema>=4.26.0,<5.0.0"
.\.venv\Scripts\python.exe -m pip show jsonschema
```

Expected: installation succeeds and `pip show` reports version `4.26.0` or a
compatible later 4.x release.

- [ ] **Step 3: Write the failing validation tests**

Create `backend/tests/test_tool_validation.py`:

```python
from typing import Any

import pytest

from app.tools import (
    Tool,
    ToolArgumentValidationError,
    ToolResult,
    ToolSchemaError,
    validate_tool_arguments,
    validate_tool_schema,
)


class MockTool(Tool):
    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(tool_name=self.name, success=True, data=arguments)


def build_tool(
    parameters_schema: dict[str, Any] | None = None,
) -> MockTool:
    return MockTool(
        name="echo",
        description="Echo validated arguments",
        parameters_schema=parameters_schema
        or {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["message"],
            "additionalProperties": False,
        },
        permission_level="read_only",
    )


def test_validate_tool_arguments_returns_defensive_plain_copy() -> None:
    arguments = {"message": "hello", "count": 2}

    validated = validate_tool_arguments(build_tool(), arguments)

    assert validated == arguments
    assert validated is not arguments


@pytest.mark.parametrize(
    ("arguments", "expected_code"),
    [
        ({"count": 1}, "required"),
        ({"message": "hello", "count": "two"}, "type"),
        ({"message": "hello", "unknown": True}, "additionalProperties"),
    ],
)
def test_validate_tool_arguments_rejects_invalid_arguments(
    arguments: dict[str, Any],
    expected_code: str,
) -> None:
    with pytest.raises(ToolArgumentValidationError) as exc_info:
        validate_tool_arguments(build_tool(), arguments)

    assert expected_code in {issue.code for issue in exc_info.value.issues}


def test_validation_issue_preserves_nested_instance_path() -> None:
    tool = build_tool(
        {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {"count": {"type": "integer"}},
                    "required": ["count"],
                    "additionalProperties": False,
                }
            },
            "required": ["config"],
            "additionalProperties": False,
        }
    )

    with pytest.raises(ToolArgumentValidationError) as exc_info:
        validate_tool_arguments(tool, {"config": {"count": "secret-value"}})

    assert exc_info.value.issues[0].path == ("config", "count")
    assert "secret-value" not in str(exc_info.value)


def test_validation_issues_have_deterministic_order_and_safe_messages() -> None:
    with pytest.raises(ToolArgumentValidationError) as exc_info:
        validate_tool_arguments(
            build_tool(),
            {
                "message": "hello",
                "count": "super-secret",
                "secret_extra": "do-not-leak",
            },
        )

    assert [issue.code for issue in exc_info.value.issues] == [
        "additionalProperties",
        "type",
    ]
    assert "super-secret" not in str(exc_info.value)
    assert "do-not-leak" not in str(exc_info.value)


def test_validate_tool_arguments_rejects_non_mapping_input() -> None:
    with pytest.raises(ToolArgumentValidationError) as exc_info:
        validate_tool_arguments(build_tool(), ["not", "an", "object"])  # type: ignore[arg-type]

    assert exc_info.value.issues[0].code == "type"


def test_validate_tool_schema_rejects_invalid_schema_without_echoing_it() -> None:
    schema = {"type": "not-a-json-schema-type"}

    with pytest.raises(ToolSchemaError) as exc_info:
        validate_tool_schema(schema)

    assert "not-a-json-schema-type" not in str(exc_info.value)
```

- [ ] **Step 4: Run the validation tests to verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_validation.py -q
```

Expected: collection fails because the validation symbols are not implemented
or exported.

- [ ] **Step 5: Implement the minimal validation module**

Create `backend/app/tools/validation.py`:

```python
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from app.tools.base import Tool, ToolError


PathPart = str | int


class ToolSchemaError(ToolError):
    """Tool 参数 schema 无法按约定安全使用。"""


@dataclass(frozen=True, slots=True)
class ToolValidationIssue:
    path: tuple[PathPart, ...]
    code: str
    message: str


class ToolArgumentValidationError(ToolError):
    def __init__(
        self,
        tool_name: str,
        issues: list[ToolValidationIssue],
    ) -> None:
        self.tool_name = tool_name
        self.issues = tuple(issues)
        summary = "; ".join(
            f"{_format_path(issue.path)} [{issue.code}] {issue.message}"
            for issue in self.issues
        )
        super().__init__(f"Invalid arguments for tool '{tool_name}': {summary}")


_SAFE_MESSAGES = {
    "additionalProperties": "unknown properties are not allowed",
    "enum": "value is not one of the allowed options",
    "maxItems": "array contains too many items",
    "maxLength": "text is too long",
    "maximum": "number is above the allowed maximum",
    "minItems": "array contains too few items",
    "minLength": "text is too short",
    "minimum": "number is below the allowed minimum",
    "pattern": "text does not match the required pattern",
    "required": "a required property is missing",
    "type": "value has an invalid type",
}


def _format_path(path: tuple[PathPart, ...]) -> str:
    if not path:
        return "$"
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in path]
    return "$/" + "/".join(escaped)


def _issue_from_error(error: ValidationError) -> ToolValidationIssue:
    code = str(error.validator or "schema")
    return ToolValidationIssue(
        path=tuple(error.absolute_path),
        code=code,
        message=_SAFE_MESSAGES.get(
            code,
            f"argument does not satisfy schema rule '{code}'",
        ),
    )


def validate_tool_schema(schema: Mapping[str, Any]) -> None:
    if not isinstance(schema, Mapping):
        raise ToolSchemaError("Tool parameter schema must be an object")
    try:
        Draft202012Validator.check_schema(dict(schema))
    except SchemaError as exc:
        raise ToolSchemaError("Invalid Tool parameter schema") from exc


def validate_tool_arguments(
    tool: Tool,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    validate_tool_schema(tool.parameters_schema)
    if not isinstance(arguments, Mapping):
        raise ToolArgumentValidationError(
            tool.name,
            [ToolValidationIssue((), "type", "arguments must be an object")],
        )

    payload = deepcopy(dict(arguments))
    validator = Draft202012Validator(tool.parameters_schema)
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: (
            tuple(str(part) for part in error.absolute_path),
            str(error.validator or "schema"),
            tuple(str(part) for part in error.absolute_schema_path),
        ),
    )
    if errors:
        raise ToolArgumentValidationError(
            tool.name,
            [_issue_from_error(error) for error in errors],
        )
    return payload
```

Update `backend/app/tools/__init__.py` to import and export
`ToolValidationIssue`, `ToolSchemaError`, `ToolArgumentValidationError`,
`validate_tool_schema`, and `validate_tool_arguments` in addition to the S2-S3
base symbols.

- [ ] **Step 6: Run the validation tests to verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_validation.py -q
```

Expected: every validation test passes and no rejected argument value appears
in failure messages.

- [ ] **Step 7: Re-run the Tool base regression tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py tests/test_tool_validation.py -q
```

Expected: the S2 base contract and S5 validation tests all pass.

---

### Task 2: In-memory Tool Registry

**Files:**
- Create: `backend/tests/test_tool_registry.py`
- Create: `backend/app/tools/registry.py`
- Modify: `backend/app/tools/__init__.py`

**Interfaces:**
- Consumes: `Tool`, `ToolError`, and `validate_tool_schema`.
- Produces: `ToolRegistry.register_tool(tool: Tool) -> None`.
- Produces: `ToolRegistry.get_tool(name: str) -> Tool`.
- Produces: `ToolRegistry.list_tools() -> list[Tool]`.
- Produces: `ToolRegistry.get_openai_tool_schemas() -> list[dict[str, Any]]`.
- Produces: `ToolRegistryError`, `DuplicateToolError`, and `ToolNotFoundError`.

- [ ] **Step 1: Write the failing Registry tests**

Create `backend/tests/test_tool_registry.py`:

```python
from typing import Any

import pytest

from app.tools import (
    DuplicateToolError,
    Tool,
    ToolNotFoundError,
    ToolRegistry,
    ToolResult,
    ToolSchemaError,
)


class MockTool(Tool):
    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(tool_name=self.name, success=True, data=arguments)


def build_tool(name: str = "echo", *, schema_type: str = "object") -> MockTool:
    return MockTool(
        name=name,
        description=f"Run {name}",
        parameters_schema={
            "type": schema_type,
            "properties": {"message": {"type": "string"}},
            "additionalProperties": False,
        },
        permission_level="read_only",
    )


def test_registry_registers_gets_and_lists_tools_in_order() -> None:
    first = build_tool("first")
    second = build_tool("second")
    registry = ToolRegistry()

    registry.register_tool(first)
    registry.register_tool(second)

    assert registry.get_tool("first") is first
    assert registry.list_tools() == [first, second]


def test_registry_list_is_a_defensive_copy() -> None:
    registry = ToolRegistry()
    registry.register_tool(build_tool())

    listed = registry.list_tools()
    listed.clear()

    assert [tool.name for tool in registry.list_tools()] == ["echo"]


def test_registry_rejects_duplicate_without_changing_state() -> None:
    original = build_tool()
    registry = ToolRegistry()
    registry.register_tool(original)

    with pytest.raises(DuplicateToolError, match="echo"):
        registry.register_tool(build_tool())

    assert registry.list_tools() == [original]


def test_registry_rejects_non_tool_instance() -> None:
    with pytest.raises(TypeError, match="Tool instance"):
        ToolRegistry().register_tool(object())  # type: ignore[arg-type]


def test_registry_rejects_invalid_schema_atomically() -> None:
    registry = ToolRegistry()

    with pytest.raises(ToolSchemaError):
        registry.register_tool(build_tool(schema_type="invalid-type"))

    assert registry.list_tools() == []


def test_registry_lookup_is_exact_and_missing_name_raises() -> None:
    registry = ToolRegistry()
    registry.register_tool(build_tool())

    with pytest.raises(ToolNotFoundError, match="echo "):
        registry.get_tool("echo ")


def test_registry_lookup_rejects_non_string_name() -> None:
    with pytest.raises(TypeError, match="tool name must be a string"):
        ToolRegistry().get_tool(1)  # type: ignore[arg-type]


def test_registry_exports_defensive_openai_function_schemas() -> None:
    tool = build_tool()
    registry = ToolRegistry()
    registry.register_tool(tool)

    schemas = registry.get_openai_tool_schemas()

    assert schemas == [
        {
            "type": "function",
            "function": {
                "name": "echo",
                "description": "Run echo",
                "parameters": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "additionalProperties": False,
                },
            },
        }
    ]
    schemas[0]["function"]["parameters"]["properties"]["message"]["type"] = "integer"
    assert tool.parameters_schema["properties"]["message"]["type"] == "string"
```

- [ ] **Step 2: Run the Registry tests to verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_registry.py -q
```

Expected: collection fails because Registry symbols are not implemented or
exported.

- [ ] **Step 3: Implement the minimal Registry**

Create `backend/app/tools/registry.py`:

```python
from copy import deepcopy
from typing import Any

from app.tools.base import Tool, ToolError
from app.tools.validation import validate_tool_schema


class ToolRegistryError(ToolError):
    """Tool 注册与发现边界的基础异常。"""


class DuplicateToolError(ToolRegistryError):
    pass


class ToolNotFoundError(ToolRegistryError):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools_by_name: dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        if not isinstance(tool, Tool):
            raise TypeError("tool must be a Tool instance")
        if tool.name in self._tools_by_name:
            raise DuplicateToolError(f"Duplicate Tool registration: {tool.name}")
        validate_tool_schema(tool.parameters_schema)
        self._tools_by_name[tool.name] = tool

    def get_tool(self, name: str) -> Tool:
        if not isinstance(name, str):
            raise TypeError("tool name must be a string")
        try:
            return self._tools_by_name[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"Tool not found: {name}") from exc

    def list_tools(self) -> list[Tool]:
        return list(self._tools_by_name.values())

    def get_openai_tool_schemas(self) -> list[dict[str, Any]]:
        return deepcopy(
            [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters_schema,
                    },
                }
                for tool in self._tools_by_name.values()
            ]
        )
```

Update `backend/app/tools/__init__.py` to import and export `ToolRegistry`,
`ToolRegistryError`, `DuplicateToolError`, and `ToolNotFoundError` while
preserving every existing base and validation export.

- [ ] **Step 4: Run the Registry tests to verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_registry.py -q
```

Expected: every Registry test passes.

- [ ] **Step 5: Run the focused Registry and validation suite**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_registry.py tests/test_tool_validation.py -q
```

Expected: Registry registration, schema validation, lookup, and export tests all
pass without executing a Tool.

---

### Task 3: Read-only Workspace Security Boundary

**Files:**
- Create: `backend/tests/test_tool_security.py`
- Create: `backend/app/tools/security.py`
- Modify: `backend/app/tools/__init__.py`

**Interfaces:**
- Consumes: `ToolError` from `app.tools.base`.
- Produces: `PROJECT_WORKSPACE_ROOT`, `DEFAULT_MAX_FILE_BYTES = 1_048_576`, and `DEFAULT_MAX_DIRECTORY_DEPTH = 3`.
- Produces: `resolve_workspace_path(path: str | Path, *, workspace_root: Path = PROJECT_WORKSPACE_ROOT) -> Path`.
- Produces: `validate_file_size(size_bytes: int, *, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES) -> int`.
- Produces: `validate_directory_depth(depth: int, *, max_depth: int = DEFAULT_MAX_DIRECTORY_DEPTH) -> int`.
- Produces: `ToolSecurityError`, `UnsafePathError`, and `ToolLimitError`.

- [ ] **Step 1: Write the failing security tests**

Create `backend/tests/test_tool_security.py`:

```python
from pathlib import Path

import pytest

from app.tools import (
    DEFAULT_MAX_DIRECTORY_DEPTH,
    DEFAULT_MAX_FILE_BYTES,
    ToolLimitError,
    UnsafePathError,
    resolve_workspace_path,
    validate_directory_depth,
    validate_file_size,
)


def test_resolve_workspace_path_accepts_safe_relative_path(tmp_path: Path) -> None:
    resolved = resolve_workspace_path(
        "docs/guide.md",
        workspace_root=tmp_path,
    )

    assert resolved == (tmp_path / "docs" / "guide.md").resolve()


def test_resolve_workspace_path_accepts_workspace_root(tmp_path: Path) -> None:
    assert resolve_workspace_path(".", workspace_root=tmp_path) == tmp_path.resolve()


@pytest.mark.parametrize("unsafe_path", ["", "   ", "safe\x00name"])
def test_resolve_workspace_path_rejects_blank_or_nul(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "/outside.txt",
        r"C:\outside.txt",
        r"C:outside.txt",
        r"\\server\share\secret.txt",
    ],
)
def test_resolve_workspace_path_rejects_absolute_drive_and_unc_paths(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    ["../outside.txt", r"docs\..\secret.txt", r"docs\.. \secret.txt"],
)
def test_resolve_workspace_path_rejects_parent_traversal(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    [
        ".env",
        ".env ",
        "config/.ENV.local",
        ".ssh/config",
        ".Git/config",
        "DOCS-LOCAL/review.md",
    ],
)
def test_resolve_workspace_path_rejects_sensitive_components(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    [".env:stream", "docs/file.txt:stream"],
)
def test_resolve_workspace_path_rejects_windows_alternate_data_streams(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "unsafe_path",
    ["id_rsa", "keys/id_ed25519", "certs/private.pem", "keys/PRIVATE.KEY"],
)
def test_resolve_workspace_path_rejects_private_key_files(
    tmp_path: Path,
    unsafe_path: str,
) -> None:
    with pytest.raises(UnsafePathError):
        resolve_workspace_path(unsafe_path, workspace_root=tmp_path)


def test_resolve_workspace_path_allows_non_secret_similar_name(tmp_path: Path) -> None:
    resolved = resolve_workspace_path("docs/keynote.md", workspace_root=tmp_path)

    assert resolved == (tmp_path / "docs" / "keynote.md").resolve()


def test_validate_file_size_accepts_limit_and_rejects_oversize() -> None:
    assert validate_file_size(DEFAULT_MAX_FILE_BYTES) == DEFAULT_MAX_FILE_BYTES
    with pytest.raises(ToolLimitError, match="file size"):
        validate_file_size(DEFAULT_MAX_FILE_BYTES + 1)


@pytest.mark.parametrize("size_bytes", [-1, True, "1"])
def test_validate_file_size_rejects_invalid_values(size_bytes: object) -> None:
    with pytest.raises((TypeError, ToolLimitError)):
        validate_file_size(size_bytes)  # type: ignore[arg-type]


def test_validate_directory_depth_accepts_limit_and_rejects_excess() -> None:
    assert (
        validate_directory_depth(DEFAULT_MAX_DIRECTORY_DEPTH)
        == DEFAULT_MAX_DIRECTORY_DEPTH
    )
    with pytest.raises(ToolLimitError, match="directory depth"):
        validate_directory_depth(DEFAULT_MAX_DIRECTORY_DEPTH + 1)


@pytest.mark.parametrize("depth", [-1, True, "1"])
def test_validate_directory_depth_rejects_invalid_values(depth: object) -> None:
    with pytest.raises((TypeError, ToolLimitError)):
        validate_directory_depth(depth)  # type: ignore[arg-type]
```

- [ ] **Step 2: Run the security tests to verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_security.py -q
```

Expected: collection fails because the security symbols are not implemented or
exported.

- [ ] **Step 3: Implement the minimal security module**

Create `backend/app/tools/security.py`:

```python
from pathlib import Path, PurePosixPath, PureWindowsPath

from app.tools.base import ToolError


PROJECT_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MAX_FILE_BYTES = 1_048_576
DEFAULT_MAX_DIRECTORY_DEPTH = 3

_SENSITIVE_DIRECTORY_NAMES = frozenset({".git", ".ssh", "docs-local"})
_PRIVATE_KEY_NAMES = frozenset({"id_dsa", "id_ecdsa", "id_ed25519", "id_rsa"})


class ToolSecurityError(ToolError):
    """Tool 的只读路径或资源限制被拒绝。"""


class UnsafePathError(ToolSecurityError):
    pass


class ToolLimitError(ToolSecurityError):
    pass


def _path_parts(raw_path: str) -> tuple[str, ...]:
    return tuple(
        part
        for part in raw_path.replace("\\", "/").split("/")
        if part not in {"", "."}
    )


def _normalize_windows_component(component: str) -> str:
    normalized = component.rstrip(" ")
    if normalized in {".", ".."}:
        return normalized
    return normalized.rstrip(".")


def _is_sensitive_component(component: str) -> bool:
    normalized = _normalize_windows_component(component).casefold()
    return (
        normalized in _SENSITIVE_DIRECTORY_NAMES
        or normalized == ".env"
        or normalized.startswith(".env.")
        or normalized in _PRIVATE_KEY_NAMES
        or normalized.endswith((".pem", ".key"))
    )


def resolve_workspace_path(
    path: str | Path,
    *,
    workspace_root: Path = PROJECT_WORKSPACE_ROOT,
) -> Path:
    if not isinstance(path, (str, Path)):
        raise TypeError("path must be a string or Path")
    raw_path = str(path)
    if not raw_path.strip() or "\x00" in raw_path:
        raise UnsafePathError("path must be non-blank and contain no NUL byte")

    windows_path = PureWindowsPath(raw_path)
    posix_path = PurePosixPath(raw_path)
    if windows_path.drive or windows_path.is_absolute() or posix_path.is_absolute():
        raise UnsafePathError("absolute, drive-qualified, and UNC paths are forbidden")

    raw_parts = _path_parts(raw_path)
    windows_normalized_parts = tuple(
        _normalize_windows_component(part) for part in raw_parts
    )
    if ".." in windows_normalized_parts:
        raise UnsafePathError("parent traversal is forbidden")
    if any(":" in part for part in raw_parts):
        raise UnsafePathError("Windows alternate data streams are forbidden")
    if any(_is_sensitive_component(part) for part in raw_parts):
        raise UnsafePathError("sensitive workspace paths are forbidden")

    root = workspace_root.resolve()
    resolved = (root / Path(raw_path)).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError("path resolves outside the workspace") from exc
    if any(_is_sensitive_component(part) for part in relative.parts):
        raise UnsafePathError("sensitive workspace paths are forbidden")
    return resolved


def _require_non_negative_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value < 0:
        raise ToolLimitError(f"{field_name} must not be negative")
    return value


def validate_file_size(
    size_bytes: int,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> int:
    size_bytes = _require_non_negative_int(size_bytes, "file size")
    max_file_bytes = _require_non_negative_int(max_file_bytes, "file size limit")
    if size_bytes > max_file_bytes:
        raise ToolLimitError("file size exceeds the allowed limit")
    return size_bytes


def validate_directory_depth(
    depth: int,
    *,
    max_depth: int = DEFAULT_MAX_DIRECTORY_DEPTH,
) -> int:
    depth = _require_non_negative_int(depth, "directory depth")
    max_depth = _require_non_negative_int(max_depth, "directory depth limit")
    if depth > max_depth:
        raise ToolLimitError("directory depth exceeds the allowed limit")
    return depth
```

Update `backend/app/tools/__init__.py` to import and export every public constant,
error, and function listed in this task while preserving all base, validation,
and Registry exports.

- [ ] **Step 4: Run the security tests to verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_security.py -q
```

Expected: every path and limit test passes using only `tmp_path`; no target file
is opened or enumerated.

- [ ] **Step 5: Run all S2-S6 focused Tool tests**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py tests/test_tool_schemas.py tests/test_tool_validation.py tests/test_tool_registry.py tests/test_tool_security.py -q
```

Expected: all Tool foundation, schema, Registry, validation, and security tests
pass without Provider, database, or filesystem I/O.

---

### Task 4: Batch 2 Verification and Acceptance Record

**Files:**
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Verify: all files changed by Tasks 1-3 plus the approved design and implementation plan.

**Interfaces:**
- Consumes: passing S4-S6 contracts and fresh full-suite evidence.
- Produces: a durable Batch 2 acceptance record without changing S7 or later status.

- [ ] **Step 1: Run complete backend verification**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
..\.venv\Scripts\python.exe -m pip show jsonschema
```

Expected: all backend tests pass; only the previously accepted Starlette
TestClient/httpx deprecation warning may remain; `pip check` reports no broken
requirements; `jsonschema` is a compatible 4.x version.

- [ ] **Step 2: Run unchanged frontend regression checks**

Run from `frontend/`:

```powershell
npm run typecheck
npm run test
npm run build
```

Expected: TypeScript checking, the complete Vitest suite, and production build
all pass.

- [ ] **Step 3: Update only the Batch 2 and S4-S6 status rows**

In `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`:

- change Batch 2 from `未完成` to `已完成`;
- mark S4 and S5 as `Codex（done）`;
- mark S6 as `Codex（done；Claude Code 未运行）` because its review is optional
  in the execution table and no external review was requested;
- leave S7, S8, Batch 3, and every later row unchanged.

- [ ] **Step 4: Add the S4-S6 acceptance record**

Append a `P2-M1-S4～S6 Tool Registry、参数校验与安全边界验收记录
（2026-07-17）` subsection after the S2-S3 record. Record these verified facts:

```markdown
| 验收项 | 结果与证据 |
|---|---|
| Tool Registry | 精确名称注册和查询、注册顺序、重复/未知名称错误、无效 schema 原子拒绝及 OpenAI function schema 防御性复制均由聚焦测试覆盖。 |
| 参数校验 | 使用 JSON Schema Draft 2020-12；缺参、类型错误、未知参数、嵌套路径、多错误稳定排序和不回显参数值均由聚焦测试覆盖。 |
| 安全边界 | 仅用 `tmp_path` 验证相对路径、绝对/盘符/UNC、`..`、Windows 尾随点/空格别名和备用数据流、工作区越界、`.env`、敏感目录、私钥、文件大小和目录深度策略；未读取任何目标文件。 |
| 全量验证 | 完整 backend pytest、`pip check`、frontend typecheck、完整 Vitest 和 production build 均通过；写入实际观察到的测试数量与唯一已知 warning。 |
| 安全与边界 | 未读取真实 `.env`、用户数据库或凭据，未调用 Provider；未实现 builtin Tool、ORM、迁移、Agent、API、前端、RAG、Memory 或 MCP。 |
```

Add a conclusion that only S4-S6 and Batch 2 are complete, that M1 remains
incomplete until S7-S8, and that the next batch is `P2-M1-S7～S8` without
implementing it now.

- [ ] **Step 5: Run formatting, scope, generated-output, and secret checks**

Run from the repository root:

```powershell
git diff --check
git -c core.quotepath=false status --short --untracked-files=all
git -c core.quotepath=false diff --name-only
git grep -n -I -E "(sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY)" -- . ":(exclude)docs-local/**"
```

Expected: only S4-S6 code/tests/dependencies, the design/plan documents, and the
Plan 2 acceptance record are changed; no build output, local database, tracked
`.env`, credential, private key, S7 ORM/migration, builtin Tool, Agent, API, or
frontend implementation appears. The secret-pattern command may return exit 1
when it finds no match; that is the expected clean result.

- [ ] **Step 6: Run Codex self-review and re-verify any correction**

Classify findings as must fix, fix later, record as limitation, or not
applicable. Confirm:

- Registry registration remains in-memory and exact-name only;
- validation preserves standard JSON Schema unknown-property semantics;
- validation errors do not include rejected values;
- security resolves but never reads paths and rejects both Windows and POSIX
  absolute forms;
- no route, Provider, database, frontend, Plan 1 release history, or S7+ module
  changed;
- no real secret or generated output is present;
- the evidence is fresh and sufficient.

Re-run focused and full verification after any code correction.

- [ ] **Step 7: Leave the verified batch for the user's manual commit**

Do not stage or commit. Report changed files, exact verification results, Codex
review conclusion, the decision that Claude Code is optional and was not run,
residual risks, next suggested batch `P2-M1-S7～S8`, and suggested commit:

```text
feat(tools): add registry validation and safety boundary
```
