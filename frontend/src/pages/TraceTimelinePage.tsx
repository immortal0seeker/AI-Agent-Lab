import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchHealth } from "../api/health";
import {
  fetchTraceRunDetail,
  fetchTraceRuns,
  TraceApiError,
} from "../api/traces";
import TraceRunList, {
  type TraceRunListState,
  traceRunTypeLabel,
  traceStatusLabel,
} from "../components/trace/TraceRunList";
import TraceStepTimeline from "../components/trace/TraceStepTimeline";
import WorkspaceSidebar, { type ApiHealth } from "../components/WorkspaceSidebar";
import type { TraceRunDetail } from "../types/trace";
import {
  buildTraceRunUrl,
  readTraceRunId,
  type WorkspaceView,
} from "../utils/agentUrl";


type TraceTimelinePageProps = {
  onSelectWorkspace: (workspace: WorkspaceView) => void;
};

type TracePageError = {
  message: string;
  requestId: string | null;
};

type TraceDetailState =
  | { status: "idle" }
  | { status: "loading"; runId: string }
  | { status: "ready"; detail: TraceRunDetail }
  | {
      status: "error";
      runId: string;
      message: string;
      requestId: string | null;
    };

export function toTracePageError(error: unknown): TracePageError {
  if (error instanceof TraceApiError) {
    return { message: error.message, requestId: error.requestId };
  }
  if (error instanceof Error) {
    return { message: error.message, requestId: null };
  }
  return { message: "Trace request failed", requestId: null };
}

export function createTraceRequestGate() {
  let generation = 0;
  return {
    begin() {
      generation += 1;
      return generation;
    },
    invalidate() {
      generation += 1;
    },
    isCurrent(candidate: number) {
      return candidate === generation;
    },
  };
}

function TraceDetailPanel({
  state,
  onRetry,
}: {
  state: TraceDetailState;
  onRetry: (runId: string) => void;
}) {
  if (state.status === "idle") {
    return (
      <div className="trace-detail-state" role="status">
        Select a Trace Run to inspect its timeline
      </div>
    );
  }
  if (state.status === "loading") {
    return (
      <div className="trace-detail-state" role="status">
        Loading Trace detail...
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <div className="trace-detail-state trace-detail-state--error" role="alert">
        <strong>{state.message}</strong>
        {state.requestId === null ? null : (
          <span>Request ID: {state.requestId}</span>
        )}
        <button
          type="button"
          aria-label="Retry Trace detail"
          onClick={() => onRetry(state.runId)}
        >
          Retry detail
        </button>
      </div>
    );
  }

  const { detail } = state;
  return (
    <article className="trace-detail">
      <header className="trace-detail__header">
        <div>
          <span>{traceRunTypeLabel(detail.run_type)}</span>
          <h2>{detail.title ?? detail.input_text}</h2>
        </div>
        <span className={`trace-status trace-status--${detail.status}`}>
          {traceStatusLabel(detail.status)}
        </span>
      </header>

      <dl className="trace-id-grid trace-detail__ids">
        <div><dt>Trace Run ID</dt><dd><code>{detail.id}</code></dd></div>
        <div><dt>Conversation ID</dt><dd><code>{detail.conversation_id ?? "—"}</code></dd></div>
        <div><dt>Agent Run ID</dt><dd><code>{detail.agent_run_id ?? "—"}</code></dd></div>
        <div><dt>User Message ID</dt><dd><code>{detail.user_message_id ?? "—"}</code></dd></div>
      </dl>

      <dl
        className="trace-id-grid trace-detail__ids"
        aria-label="Trace Run metrics"
      >
        <div>
          <dt>Input Tokens</dt>
          <dd>{detail.total_input_tokens ?? "—"}</dd>
        </div>
        <div>
          <dt>Output Tokens</dt>
          <dd>{detail.total_output_tokens ?? "—"}</dd>
        </div>
        <div>
          <dt>Total Tokens</dt>
          <dd>{detail.total_tokens ?? "—"}</dd>
        </div>
        <div>
          <dt>Estimated Cost</dt>
          <dd>{detail.estimated_cost ?? "—"}</dd>
        </div>
        <div>
          <dt>Run Latency</dt>
          <dd>
            {detail.latency_ms === null ? "—" : `${detail.latency_ms} ms`}
          </dd>
        </div>
      </dl>

      {detail.error_message === null ? null : (
        <p className="trace-error" role="alert">{detail.error_message}</p>
      )}

      <section className="trace-detail__io">
        <div><h3>Input</h3><p>{detail.input_text}</p></div>
        <div><h3>Output</h3><p>{detail.output_text ?? "No output recorded"}</p></div>
      </section>

      <details className="trace-run-metadata">
        <summary>Run metadata</summary>
        <pre>{JSON.stringify(detail.metadata_json, null, 2)}</pre>
      </details>

      <TraceStepTimeline detail={detail} />
    </article>
  );
}


export default function TraceTimelinePage({
  onSelectWorkspace,
}: TraceTimelinePageProps) {
  const initialRunId = useMemo(
    () => readTraceRunId(window.location.search),
    [],
  );
  const mountedRef = useRef(false);
  const selectedIdRef = useRef<string | null>(initialRunId);
  const listGateRef = useRef(createTraceRequestGate());
  const detailGateRef = useRef(createTraceRequestGate());
  const [health, setHealth] = useState<ApiHealth>({ status: "checking" });
  const [listState, setListState] = useState<TraceRunListState>({
    status: "loading",
  });
  const [selectedId, setSelectedId] = useState<string | null>(initialRunId);
  const [detailState, setDetailState] = useState<TraceDetailState>(
    initialRunId === null
      ? { status: "idle" }
      : { status: "loading", runId: initialRunId },
  );

  const loadDetail = useCallback(async (runId: string) => {
    const generation = detailGateRef.current.begin();
    setDetailState({ status: "loading", runId });
    try {
      const detail = await fetchTraceRunDetail(runId);
      if (mountedRef.current && detailGateRef.current.isCurrent(generation)) {
        setDetailState({ status: "ready", detail });
      }
    } catch (error) {
      if (mountedRef.current && detailGateRef.current.isCurrent(generation)) {
        setDetailState({ status: "error", runId, ...toTracePageError(error) });
      }
    }
  }, []);

  const selectRun = useCallback(
    (runId: string) => {
      selectedIdRef.current = runId;
      setSelectedId(runId);
      window.history.replaceState(
        null,
        "",
        buildTraceRunUrl(window.location.href, runId),
      );
      void loadDetail(runId);
    },
    [loadDetail],
  );

  const loadList = useCallback(async () => {
    const generation = listGateRef.current.begin();
    setListState({ status: "loading" });
    try {
      const runs = await fetchTraceRuns();
      if (!mountedRef.current || !listGateRef.current.isCurrent(generation)) {
        return;
      }
      setListState({ status: "ready", runs });
      if (selectedIdRef.current === null && runs.length > 0) {
        selectRun(runs[0].id);
      }
    } catch (error) {
      if (mountedRef.current && listGateRef.current.isCurrent(generation)) {
        setListState({ status: "error", ...toTracePageError(error) });
      }
    }
  }, [selectRun]);

  useEffect(() => {
    mountedRef.current = true;
    void fetchHealth()
      .then((response) => {
        if (mountedRef.current) {
          setHealth({ status: "healthy", service: response.service });
        }
      })
      .catch((error: unknown) => {
        if (mountedRef.current) {
          setHealth({
            status: "error",
            message: error instanceof Error ? error.message : "Health check failed",
          });
        }
      });
    void loadList();
    if (initialRunId !== null) {
      void loadDetail(initialRunId);
    }
    return () => {
      mountedRef.current = false;
      listGateRef.current.invalidate();
      detailGateRef.current.invalidate();
    };
  }, [initialRunId, loadDetail, loadList]);

  return (
    <main className="workspace-shell">
      <WorkspaceSidebar
        activeWorkspace="trace"
        health={health}
        onSelectWorkspace={onSelectWorkspace}
      />
      <section className="trace-workspace">
        <header className="trace-header">
          <div>
            <h1>Trace</h1>
            <p>Trace Timeline workspace</p>
          </div>
        </header>
        <div className="trace-layout">
          <aside className="trace-list-pane" aria-label="Recent Trace Runs">
            <header>
              <h2>Recent Runs</h2>
              <span>Latest 50</span>
            </header>
            <TraceRunList
              state={listState}
              selectedId={selectedId}
              onSelect={selectRun}
              onRetry={() => void loadList()}
            />
          </aside>
          <section className="trace-detail-pane" aria-label="Trace Run detail">
            <TraceDetailPanel state={detailState} onRetry={loadDetail} />
          </section>
        </div>
      </section>
    </main>
  );
}
