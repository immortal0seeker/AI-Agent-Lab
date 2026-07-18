from app.providers.llm.base import LLMFunctionDefinition, LLMToolDefinition
from app.tools.registry import ToolRegistry


def build_llm_tool_definitions(
    registry: ToolRegistry,
) -> tuple[LLMToolDefinition, ...]:
    if not isinstance(registry, ToolRegistry):
        raise TypeError("registry must be a ToolRegistry")
    return tuple(
        LLMToolDefinition(
            function=LLMFunctionDefinition(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters_schema,
            )
        )
        for tool in registry.list_tools()
    )
