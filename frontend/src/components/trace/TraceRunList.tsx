import type { TraceRunSummary, TraceRunType, TraceStatus } from "../../types/trace";


export type TraceRunListState =
  | { status: "loading" }
  | { status: "ready"; runs: TraceRunSummary[] }
  | { status: "error"; message: string; requestId: string | null };

type TraceRunListProps = {
  state: TraceRunListState;
  selectedId: string | null;
  onSelect: (runId: string) => void;
  onRetry: () => void;
};

const RUN_TYPE_LABELS: Record<TraceRunType, string> = {
  chat: "Chat",
  agent: "Agent",
  rag_query: "RAG Query",
  rag_chat: "RAG Chat",
  evaluation: "Evaluation",
  tool: "Tool",
};

const STATUS_LABELS: Record<TraceStatus, string> = {
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

export function traceRunTypeLabel(runType: TraceRunType): string {
  return RUN_TYPE_LABELS[runType];
}

export function traceStatusLabel(status: TraceStatus): string {
  return STATUS_LABELS[status];
}

export default function TraceRunList({
  state,
  selectedId,
  onSelect,
  onRetry,
}: TraceRunListProps) {
  if (state.status === "loading") {
    return (
      <div className="trace-list-state" role="status">
        Loading recent Trace Runs...
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="trace-list-state trace-list-state--error" role="alert">
        <strong>{state.message}</strong>
        {state.requestId === null ? null : (
          <span>Request ID: {state.requestId}</span>
        )}
        <button type="button" aria-label="Retry Trace list" onClick={onRetry}>
          Retry list
        </button>
      </div>
    );
  }

  if (state.runs.length === 0) {
    return (
      <div className="trace-list-state" role="status">
        No Trace Runs recorded yet
      </div>
    );
  }

  return (
    <div className="trace-run-list">
      {state.runs.map((run) => (
        <button
          key={run.id}
          type="button"
          aria-label={`View Trace ${run.id}`}
          aria-current={selectedId === run.id ? "true" : undefined}
          onClick={() => onSelect(run.id)}
        >
          <span className="trace-run-list__labels">
            <strong>{traceRunTypeLabel(run.run_type)}</strong>
            <span className={`trace-status trace-status--${run.status}`}>
              {traceStatusLabel(run.status)}
            </span>
          </span>
          <span className="trace-run-list__preview">{run.input_preview}</span>
          <code>{run.id}</code>
          <time dateTime={run.created_at}>{run.created_at}</time>
        </button>
      ))}
    </div>
  );
}
