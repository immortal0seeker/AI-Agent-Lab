from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.agents import SimpleAgentService
from app.api.dependencies import get_agent_service, get_simple_agent_service
from app.models import AgentRun, ToolCall
from app.schemas.agent import (
    AgentRunCreate,
    AgentRunExecutionRead,
    AgentRunRead,
    ToolCallRead,
)
from app.services.agent_service import AgentService


router = APIRouter(prefix="/agents/runs", tags=["agents"])


def to_agent_run_read(row: AgentRun) -> AgentRunRead:
    return AgentRunRead(
        id=row.id,
        conversation_id=row.conversation_id,
        user_message_id=row.user_message_id,
        status=row.status,
        goal=row.goal,
        final_answer=row.final_answer,
        error=row.error_message,
        started_at=row.started_at,
        ended_at=row.ended_at,
        latency_ms=row.latency_ms,
        created_at=row.created_at,
    )


def to_tool_call_read(row: ToolCall) -> ToolCallRead:
    return ToolCallRead(
        id=row.id,
        tool_call_id=row.tool_call_id,
        agent_run_id=row.agent_run_id,
        conversation_id=row.conversation_id,
        tool_name=row.tool_name,
        arguments=row.arguments_json,
        result=row.result_json,
        status=row.status,
        error=row.error_message,
        started_at=row.started_at,
        ended_at=row.ended_at,
        latency_ms=row.latency_ms,
        created_at=row.created_at,
    )


@router.post(
    "",
    response_model=AgentRunExecutionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_agent_run(
    data: AgentRunCreate,
    service: AgentService = Depends(get_agent_service),
    runner: SimpleAgentService = Depends(get_simple_agent_service),
) -> AgentRunExecutionRead:
    result = await service.run(data, runner=runner)
    return AgentRunExecutionRead(
        **to_agent_run_read(result.agent_run).model_dump(),
        tool_calls=[to_tool_call_read(row) for row in result.tool_calls],
    )


@router.get("/{run_id}", response_model=AgentRunRead)
def get_agent_run(
    run_id: UUID,
    service: AgentService = Depends(get_agent_service),
) -> AgentRunRead:
    return to_agent_run_read(service.get_agent_run(run_id))


@router.get("/{run_id}/tool-calls", response_model=list[ToolCallRead])
def list_agent_run_tool_calls(
    run_id: UUID,
    service: AgentService = Depends(get_agent_service),
) -> list[ToolCallRead]:
    return [
        to_tool_call_read(row)
        for row in service.list_tool_calls(run_id)
    ]
