from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RagRetrievalCandidate, RagRetrievalRun, TraceRun, TraceStep


@dataclass(frozen=True, slots=True)
class TraceRunListItem:
    record: TraceRun
    input_preview: str


@dataclass(frozen=True, slots=True)
class TraceRetrievalDetail:
    record: RagRetrievalRun
    candidates: tuple[RagRetrievalCandidate, ...]


@dataclass(frozen=True, slots=True)
class TraceDetail:
    record: TraceRun
    steps: tuple[TraceStep, ...]
    retrievals: tuple[TraceRetrievalDetail, ...]


class TraceRunNotFoundError(Exception):
    def __init__(self, trace_run_id: UUID) -> None:
        self.trace_run_id = trace_run_id
        super().__init__("Trace run not found")


class TraceQueryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_trace_runs(self, *, limit: int) -> list[TraceRunListItem]:
        statement = (
            select(TraceRun)
            .order_by(TraceRun.created_at.desc(), TraceRun.id.desc())
            .limit(limit)
        )
        return [
            TraceRunListItem(
                record=row,
                input_preview=_input_preview(row.input_text),
            )
            for row in self._session.scalars(statement)
        ]

    def get_trace_detail(self, trace_run_id: UUID) -> TraceDetail:
        record = self._session.get(TraceRun, trace_run_id)
        if record is None:
            raise TraceRunNotFoundError(trace_run_id)

        steps = tuple(
            self._session.scalars(
                select(TraceStep)
                .where(TraceStep.trace_run_id == trace_run_id)
                .order_by(TraceStep.step_index, TraceStep.id)
            )
        )
        retrieval_rows = tuple(
            self._session.scalars(
                select(RagRetrievalRun)
                .where(RagRetrievalRun.trace_run_id == trace_run_id)
                .order_by(RagRetrievalRun.created_at, RagRetrievalRun.id)
            )
        )
        retrieval_ids = [row.id for row in retrieval_rows]
        candidate_rows = (
            ()
            if not retrieval_ids
            else tuple(
                self._session.scalars(
                    select(RagRetrievalCandidate)
                    .where(
                        RagRetrievalCandidate.retrieval_run_id.in_(retrieval_ids)
                    )
                    .order_by(
                        RagRetrievalCandidate.retrieval_run_id,
                        RagRetrievalCandidate.rank,
                        RagRetrievalCandidate.id,
                    )
                )
            )
        )
        grouped: dict[UUID, list[RagRetrievalCandidate]] = {
            row.id: [] for row in retrieval_rows
        }
        for candidate in candidate_rows:
            grouped[candidate.retrieval_run_id].append(candidate)

        return TraceDetail(
            record=record,
            steps=steps,
            retrievals=tuple(
                TraceRetrievalDetail(row, tuple(grouped[row.id]))
                for row in retrieval_rows
            ),
        )


def _input_preview(value: str) -> str:
    if len(value) <= 160:
        return value
    return value[:159] + "…"
