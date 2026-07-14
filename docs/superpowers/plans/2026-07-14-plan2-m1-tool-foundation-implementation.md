# Plan 2 M1 Tool Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Repository instructions prohibit sub-agent execution for this batch.

**Goal:** Complete `P2-M1-S2` through `P2-M1-S3` with a validated Tool base contract and strict Tool Call schemas.

**Architecture:** `app/tools/base.py` owns executable domain contracts and does not depend on API, ORM, Provider, or service modules. `app/schemas/tool.py` owns transport serialization and may reuse `ToolResult`; focused tests drive both boundaries before implementation.

**Tech Stack:** Python 3.11, Pydantic 2, pytest 9, standard-library `abc`, `copy`, and `typing`.

## Global Constraints

- Work only on `P2-M1-S2` through `P2-M1-S3`.
- Do not implement Tool Registry, JSON Schema argument validation, path security, built-in tools, persistence, Provider tools, Agent Loop, API routes, or frontend behavior.
- Do not read a real `.env`, user database, credentials, SSH keys, browser profiles, or system credential stores.
- Use in-process Mock Tool objects only; do not call a Provider, external API, filesystem Tool, or paid service.
- Add Chinese comments or docstrings only where they clarify a non-obvious boundary.
- Keep SQLite as the default long-term database; this batch makes no database change.
- Do not stage, commit, push, tag, or create a PR; the user commits manually.

---

### Task 1: Tool Base Contract

**Files:**
- Create: `backend/tests/test_tool_base.py`
- Create: `backend/app/tools/__init__.py`
- Create: `backend/app/tools/base.py`

**Interfaces:**
- Produces: `Tool(name, description, parameters_schema, permission_level, timeout_seconds=30.0)`.
- Produces: `async Tool.run(arguments: dict[str, Any]) -> ToolResult`.
- Produces: `ToolResult(tool_name, success, content="", data=None, error=None, metadata={})`.
- Produces: `ToolError`, the Tool-boundary base runtime exception.

- [ ] **Step 1: Write failing Tool contract tests**

Create `backend/tests/test_tool_base.py` with a concrete `MockTool` and tests that:

```python
import asyncio
from typing import Any

import pytest
from pydantic import ValidationError

from app.tools import Tool, ToolError, ToolResult


class MockTool(Tool):
    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=True,
            content=str(arguments["value"]),
        )


def build_tool(**overrides: object) -> MockTool:
    values: dict[str, object] = {
        "name": "echo",
        "description": "Echo one value",
        "parameters_schema": {
            "type": "object",
            "properties": {"value": {"type": "string"}},
        },
        "permission_level": "read_only",
        "timeout_seconds": 5,
    }
    values.update(overrides)
    return MockTool(**values)  # type: ignore[arg-type]
```

Cover successful async execution, normalized text metadata, rejection of blank
or overlong names, rejection of blank descriptions/permissions, rejection of
non-mapping schemas, rejection of boolean/string/non-positive timeouts, deep
copying of the caller's parameter schema, `ToolError` inheritance from
`RuntimeError`, ToolResult success/error consistency, rejection of unknown
fields, and isolated metadata defaults.

- [ ] **Step 2: Run the Tool tests to verify RED**

Run from `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py -q
```

Expected: collection fails because `app.tools` does not exist.

- [ ] **Step 3: Implement the minimal Tool contract**

Create `backend/app/tools/base.py` with:

```python
from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import deepcopy
from typing import Annotated, Any, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


ToolName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: ToolName
    success: bool
    content: str = ""
    data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_error_state(self) -> Self:
        if self.success and self.error is not None:
            raise ValueError("successful tool results must not include an error")
        if not self.success:
            if self.error is None or not self.error.strip():
                raise ValueError("failed tool results require a non-blank error")
            self.error = self.error.strip()
        return self


class ToolError(RuntimeError):
    """Tool 边界的基础异常。"""


class Tool(ABC):
    def __init__(
        self,
        *,
        name: str,
        description: str,
        parameters_schema: Mapping[str, Any],
        permission_level: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.name = self._normalize_text(name, "name", max_length=100)
        self.description = self._normalize_text(description, "description")
        self.permission_level = self._normalize_text(
            permission_level,
            "permission_level",
        )
        if not isinstance(parameters_schema, Mapping):
            raise TypeError("parameters_schema must be a mapping")
        if isinstance(timeout_seconds, bool) or not isinstance(
            timeout_seconds,
            (int, float),
        ):
            raise TypeError("timeout_seconds must be a number")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self.parameters_schema = deepcopy(dict(parameters_schema))
        self.timeout_seconds = float(timeout_seconds)

    @staticmethod
    def _normalize_text(
        value: str,
        field_name: str,
        *,
        max_length: int | None = None,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{field_name} must not be blank")
        if max_length is not None and len(normalized) > max_length:
            raise ValueError(f"{field_name} must be at most {max_length} characters")
        return normalized

    @abstractmethod
    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        raise NotImplementedError
```

Create `backend/app/tools/__init__.py` exporting `Tool`, `ToolError`, and
`ToolResult` through `__all__`.

- [ ] **Step 4: Run the Tool tests to verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py -q
```

Expected: all Tool base tests pass.

- [ ] **Step 5: Review Task 1 scope**

Run:

```powershell
git diff --check -- app/tools tests/test_tool_base.py
```

Expected: exit code 0; no Registry, security, builtin, ORM, API, or Agent file exists.

---

### Task 2: Tool Call Schemas

**Files:**
- Create: `backend/tests/test_tool_schemas.py`
- Create: `backend/app/schemas/tool.py`
- Modify: `backend/app/schemas/__init__.py`

**Interfaces:**
- Consumes: `app.tools.ToolResult`.
- Produces: `ToolCallStatus = Literal["pending", "running", "success", "failed", "timeout", "blocked"]`.
- Produces: `ToolCallRequest(tool_call_id, tool_name, arguments={})`.
- Produces: `ToolCallResponse(tool_call_id, tool_name, status, result=None)`.

- [ ] **Step 1: Write failing Tool Call schema tests**

Create `backend/tests/test_tool_schemas.py`. Import the three public schema
symbols from `app.schemas` and cover:

```python
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas import ToolCallRequest, ToolCallResponse
from app.tools import ToolResult


def successful_result(tool_name: str = "echo") -> ToolResult:
    return ToolResult(tool_name=tool_name, success=True, content="ok")


def failed_result(tool_name: str = "echo") -> ToolResult:
    return ToolResult(
        tool_name=tool_name,
        success=False,
        error="tool failed",
    )
```

Test identifier normalization, isolated argument defaults, blank IDs/names,
invalid statuses, unknown top-level fields, pending/running results being absent,
terminal results being required, status/result success agreement, and matching
response/result tool names.

- [ ] **Step 2: Run the schema tests to verify RED**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_schemas.py -q
```

Expected: collection fails because Tool Call schemas are not exported.

- [ ] **Step 3: Implement strict Tool Call schemas**

Create `backend/app/schemas/tool.py` with:

```python
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.tools import ToolResult


ToolCallStatus = Literal[
    "pending",
    "running",
    "success",
    "failed",
    "timeout",
    "blocked",
]
ToolCallIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
ToolIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: ToolCallIdentifier
    tool_name: ToolIdentifier
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: ToolCallIdentifier
    tool_name: ToolIdentifier
    status: ToolCallStatus
    result: ToolResult | None = None

    @model_validator(mode="after")
    def validate_result_state(self) -> Self:
        if self.status in {"pending", "running"}:
            if self.result is not None:
                raise ValueError("non-terminal tool calls must not include a result")
            return self
        if self.result is None:
            raise ValueError("terminal tool calls require a result")
        if self.result.tool_name != self.tool_name:
            raise ValueError("tool call and result names must match")
        if (self.status == "success") != self.result.success:
            raise ValueError("tool call status and result success must agree")
        return self
```

Update `backend/app/schemas/__init__.py` to import and export
`ToolCallRequest`, `ToolCallResponse`, and `ToolCallStatus`.

- [ ] **Step 4: Run the schema tests to verify GREEN**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_schemas.py -q
```

Expected: all Tool Call schema tests pass.

- [ ] **Step 5: Run the focused S2-S3 suite**

```powershell
..\.venv\Scripts\python.exe -m pytest tests/test_tool_base.py tests/test_tool_schemas.py -q
```

Expected: all focused tests pass with no external calls.

---

### Task 3: Batch 1 Verification And Record

**Files:**
- Modify: `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`
- Verify: all files changed in Tasks 1-2 and the approved design/plan documents.

**Interfaces:**
- Consumes: passing S2-S3 contracts and test evidence.
- Produces: a durable Batch 1 completion record without changing S4 or later status.

- [ ] **Step 1: Run complete backend verification**

From `backend/`:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe -m pip check
```

Expected: all backend tests pass; `pip check` reports no broken requirements.

- [ ] **Step 2: Run unchanged frontend regression checks**

From `frontend/`:

```powershell
npm run typecheck
npm run test
npm run build
```

Expected: typecheck, the complete Vitest suite, and production build pass.

- [ ] **Step 3: Update the Plan 2 execution table**

In `docs-plan/02-PLAN2/02-PLAN2-执行步骤表 (V1.0).md`:

- mark Batch 1 complete;
- mark S2 and S3 review cells `Codex（done）`;
- add a `P2-M1-S2～S3` acceptance subsection recording the implemented
  contracts, focused/full test results, mock-only behavior, and unchanged S4+
  boundary;
- leave every S4 and later implementation row unchanged.

- [ ] **Step 4: Run documentation and scope checks**

From the repository root:

```powershell
git diff --check
git -c core.quotepath=false status --short --untracked-files=all
git -c core.quotepath=false diff --name-only
```

Also verify tracked text has no credential/private-key pattern, no real `.env`
path is tracked or present, and none of these later-step paths exists:

```text
backend/app/tools/registry.py
backend/app/tools/security.py
backend/app/tools/builtin/
backend/app/agents/
```

Expected: only S2-S3 code, tests, design/plan documents, and the Plan 2 execution
record are changed; no secret or future implementation appears.

- [ ] **Step 5: Run Codex self-review**

Classify findings as must fix, fix later, record as limitation, or not applicable.
Confirm routes, Provider contracts, database models, frontend behavior, and Plan
1 release history are unchanged. Re-run affected verification after any fix.

- [ ] **Step 6: Leave the verified batch for manual commit**

Do not stage or commit. Report the changed files, verification evidence, review
decision, residual risks, next suggested batch `P2-M1-S4～S6`, and a suggested
commit message.
