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
