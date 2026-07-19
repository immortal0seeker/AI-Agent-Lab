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


def test_tool_contract_runs_asynchronously() -> None:
    result = asyncio.run(build_tool().run({"value": "hello"}))

    assert result == ToolResult(
        tool_name="echo",
        success=True,
        content="hello",
    )


def test_tool_normalizes_text_metadata() -> None:
    tool = build_tool(
        name="  echo  ",
        description="  Echo one value  ",
        permission_level="  read_only  ",
    )

    assert tool.name == "echo"
    assert tool.description == "Echo one value"
    assert tool.permission_level == "read_only"
    assert tool.timeout_seconds == 5.0


@pytest.mark.parametrize("field_name", ["name", "description", "permission_level"])
def test_tool_rejects_blank_text_metadata(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} must not be blank"):
        build_tool(**{field_name: "   "})


def test_tool_rejects_overlong_name() -> None:
    with pytest.raises(ValueError, match="name must be at most 64 characters"):
        build_tool(name="x" * 65)


@pytest.mark.parametrize("name", ["two words", "tool.name", "tool/name", "工具"])
def test_tool_rejects_provider_incompatible_name(name: str) -> None:
    with pytest.raises(ValueError, match="letters, numbers, underscores, and hyphens"):
        build_tool(name=name)


def test_tool_requires_parameter_schema_mapping() -> None:
    with pytest.raises(TypeError, match="parameters_schema must be a mapping"):
        build_tool(parameters_schema=["not", "a", "mapping"])


@pytest.mark.parametrize("timeout_seconds", [True, "5"])
def test_tool_rejects_non_numeric_timeout(timeout_seconds: object) -> None:
    with pytest.raises(TypeError, match="timeout_seconds must be a number"):
        build_tool(timeout_seconds=timeout_seconds)


@pytest.mark.parametrize("timeout_seconds", [0, -1])
def test_tool_rejects_non_positive_timeout(timeout_seconds: int) -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be greater than zero"):
        build_tool(timeout_seconds=timeout_seconds)


@pytest.mark.parametrize(
    "timeout_seconds",
    [float("nan"), float("inf"), float("-inf")],
)
def test_tool_rejects_non_finite_timeout(timeout_seconds: float) -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be finite"):
        build_tool(timeout_seconds=timeout_seconds)


def test_tool_copies_parameter_schema_from_caller() -> None:
    parameter_schema = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
    }
    tool = build_tool(parameters_schema=parameter_schema)

    parameter_schema["properties"]["value"]["type"] = "integer"

    assert tool.parameters_schema["properties"]["value"]["type"] == "string"


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


def test_tool_error_is_runtime_error() -> None:
    assert issubclass(ToolError, RuntimeError)


def test_tool_result_normalizes_failed_error() -> None:
    result = ToolResult(
        tool_name="echo",
        success=False,
        error="  tool failed  ",
    )

    assert result.error == "tool failed"


def test_successful_tool_result_rejects_error() -> None:
    with pytest.raises(
        ValidationError,
        match="successful tool results must not include an error",
    ):
        ToolResult(tool_name="echo", success=True, error="unexpected")


@pytest.mark.parametrize("error", [None, "   "])
def test_failed_tool_result_requires_non_blank_error(error: str | None) -> None:
    with pytest.raises(
        ValidationError,
        match="failed tool results require a non-blank error",
    ):
        ToolResult(tool_name="echo", success=False, error=error)


def test_tool_result_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ToolResult(
            tool_name="echo",
            success=True,
            unexpected="value",
        )


def test_tool_result_metadata_defaults_are_isolated() -> None:
    first = ToolResult(tool_name="echo", success=True)
    second = ToolResult(tool_name="echo", success=True)

    first.metadata["source"] = "first"

    assert second.metadata == {}
