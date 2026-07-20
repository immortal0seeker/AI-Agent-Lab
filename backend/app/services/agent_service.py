from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import (
    AgentRunNotFoundError,
    SimpleAgentRequest,
    SimpleAgentResult,
    SimpleAgentService,
)
from app.models import AgentRun, ToolCall
from app.schemas.agent import AgentRunCreate


class AgentService:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def run(
        self,
        data: AgentRunCreate,
        *,
        runner: SimpleAgentService,
    ) -> SimpleAgentResult:
        return await runner.run(
            SimpleAgentRequest(
                conversation_id=data.conversation_id,
                provider=data.provider,
                model=data.model,
                content=data.input,
                temperature=data.temperature,
                max_tokens=data.max_tokens,
                max_steps=data.max_steps,
            )
        )

    def get_agent_run(self, run_id: UUID) -> AgentRun:
        row = self._session.get(AgentRun, run_id)
        if row is None:
            raise AgentRunNotFoundError(run_id)
        return row

    def list_tool_calls(self, run_id: UUID) -> list[ToolCall]:
        self.get_agent_run(run_id)
        statement = (
            select(ToolCall)
            .where(ToolCall.agent_run_id == run_id)
            .order_by(ToolCall.sequence_index)
        )
        return list(self._session.scalars(statement))
