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


def test_tool_call_request_normalizes_identifiers() -> None:
    request = ToolCallRequest(
        tool_call_id="  call-1  ",
        tool_name="  echo  ",
        arguments={"value": "hello"},
    )

    assert request.tool_call_id == "call-1"
    assert request.tool_name == "echo"
    assert request.arguments == {"value": "hello"}


def test_tool_call_request_argument_defaults_are_isolated() -> None:
    first = ToolCallRequest(tool_call_id="call-1", tool_name="echo")
    second = ToolCallRequest(tool_call_id="call-2", tool_name="echo")

    first.arguments["value"] = "first"

    assert second.arguments == {}


@pytest.mark.parametrize("field_name", ["tool_call_id", "tool_name"])
def test_tool_call_request_rejects_blank_identifier(field_name: str) -> None:
    values = {"tool_call_id": "call-1", "tool_name": "echo"}
    values[field_name] = "   "

    with pytest.raises(ValidationError):
        ToolCallRequest(**values)


def test_tool_call_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ToolCallRequest(
            tool_call_id="call-1",
            tool_name="echo",
            unexpected="value",
        )


def test_tool_call_response_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        ToolCallResponse(
            tool_call_id="call-1",
            tool_name="echo",
            status="cancelled",
        )


@pytest.mark.parametrize("status", ["pending", "running"])
def test_non_terminal_tool_call_accepts_no_result(status: str) -> None:
    response = ToolCallResponse(
        tool_call_id="call-1",
        tool_name="echo",
        status=status,
    )

    assert response.result is None


@pytest.mark.parametrize("status", ["pending", "running"])
def test_non_terminal_tool_call_rejects_result(status: str) -> None:
    with pytest.raises(
        ValidationError,
        match="non-terminal tool calls must not include a result",
    ):
        ToolCallResponse(
            tool_call_id="call-1",
            tool_name="echo",
            status=status,
            result=successful_result(),
        )


@pytest.mark.parametrize("status", ["success", "failed", "timeout", "blocked"])
def test_terminal_tool_call_requires_result(status: str) -> None:
    with pytest.raises(ValidationError, match="terminal tool calls require a result"):
        ToolCallResponse(
            tool_call_id="call-1",
            tool_name="echo",
            status=status,
        )


@pytest.mark.parametrize(
    ("status", "result"),
    [
        ("success", failed_result()),
        ("failed", successful_result()),
        ("timeout", successful_result()),
        ("blocked", successful_result()),
    ],
)
def test_terminal_tool_call_requires_matching_result_success(
    status: str,
    result: ToolResult,
) -> None:
    with pytest.raises(
        ValidationError,
        match="tool call status and result success must agree",
    ):
        ToolCallResponse(
            tool_call_id="call-1",
            tool_name="echo",
            status=status,
            result=result,
        )


def test_tool_call_response_requires_matching_tool_name() -> None:
    with pytest.raises(
        ValidationError,
        match="tool call and result names must match",
    ):
        ToolCallResponse(
            tool_call_id="call-1",
            tool_name="echo",
            status="success",
            result=successful_result(tool_name="other"),
        )


@pytest.mark.parametrize(
    ("status", "result"),
    [
        ("success", successful_result()),
        ("failed", failed_result()),
        ("timeout", failed_result()),
        ("blocked", failed_result()),
    ],
)
def test_terminal_tool_call_accepts_consistent_result(
    status: str,
    result: ToolResult,
) -> None:
    response = ToolCallResponse(
        tool_call_id="call-1",
        tool_name="echo",
        status=status,
        result=result,
    )

    assert response.result == result


def test_tool_call_response_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ToolCallResponse(
            tool_call_id="call-1",
            tool_name="echo",
            status="pending",
            unexpected="value",
        )
