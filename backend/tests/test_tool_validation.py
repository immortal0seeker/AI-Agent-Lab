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
        validate_tool_arguments(
            build_tool(),
            ["not", "an", "object"],  # type: ignore[arg-type]
        )

    assert exc_info.value.issues[0].code == "type"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_validate_tool_arguments_rejects_non_standard_json_numbers(
    value: float,
) -> None:
    tool = build_tool(
        {
            "type": "object",
            "properties": {"value": {"type": "number"}},
            "required": ["value"],
            "additionalProperties": False,
        }
    )

    with pytest.raises(ToolArgumentValidationError) as exc_info:
        validate_tool_arguments(tool, {"value": value})

    assert len(exc_info.value.issues) == 1
    assert exc_info.value.issues[0].path == ()
    assert exc_info.value.issues[0].code == "json"
    assert (
        exc_info.value.issues[0].message
        == "arguments must contain only standard JSON values"
    )
    assert repr(value) not in str(exc_info.value)


def test_validate_tool_arguments_rejects_oversized_json_payload() -> None:
    oversized = "x" * 70_000

    with pytest.raises(ToolArgumentValidationError) as exc_info:
        validate_tool_arguments(build_tool(), {"message": oversized})

    assert len(exc_info.value.issues) == 1
    assert exc_info.value.issues[0].path == ()
    assert exc_info.value.issues[0].code == "json_size"
    assert (
        exc_info.value.issues[0].message
        == "arguments exceed the allowed JSON size"
    )
    assert oversized not in str(exc_info.value)


def test_validate_tool_schema_rejects_invalid_schema_without_echoing_it() -> None:
    schema = {"type": "not-a-json-schema-type"}

    with pytest.raises(ToolSchemaError) as exc_info:
        validate_tool_schema(schema)

    assert "not-a-json-schema-type" not in str(exc_info.value)


def test_validate_tool_schema_requires_object_root() -> None:
    with pytest.raises(ToolSchemaError, match="root must be an object"):
        validate_tool_schema({"type": "string"})


def test_validate_tool_schema_requires_json_serializable_values() -> None:
    with pytest.raises(ToolSchemaError, match="JSON serializable"):
        validate_tool_schema(
            {
                "type": "object",
                "properties": {"value": {"enum": [{"not-json"}]}},
            }
        )
