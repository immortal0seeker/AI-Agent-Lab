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
    schemas[0]["function"]["parameters"]["properties"]["message"][
        "type"
    ] = "integer"
    assert tool.parameters_schema["properties"]["message"]["type"] == "string"


def test_registered_tool_definition_cannot_drift_from_registry_key() -> None:
    tool = build_tool()
    registry = ToolRegistry()
    registry.register_tool(tool)

    with pytest.raises(AttributeError):
        tool.name = "renamed"  # type: ignore[misc]
    exposed = tool.parameters_schema
    exposed["type"] = "string"

    assert registry.get_tool("echo") is tool
    assert registry.get_openai_tool_schemas()[0]["function"]["name"] == "echo"
    assert (
        registry.get_openai_tool_schemas()[0]["function"]["parameters"]["type"]
        == "object"
    )


def test_registry_rejects_non_object_schema_atomically() -> None:
    registry = ToolRegistry()

    with pytest.raises(ToolSchemaError, match="root must be an object"):
        registry.register_tool(build_tool(schema_type="string"))

    assert registry.list_tools() == []
