import {
  Bot,
  CircleAlert,
  CircleOff,
  LoaderCircle,
} from "lucide-react";

import type {
  AgentRunExecution,
  AgentRunStatus,
} from "../../types/agent";
import ToolCallTimeline from "./ToolCallTimeline";
import { formatLatency } from "./toolCallView";

export type AgentRunViewState =
  | { status: "loading"; message: string }
  | { status: "empty" }
  | { status: "no-models" }
  | { status: "error"; message: string; requestId: string | null }
  | { status: "result"; run: AgentRunExecution };

const RUN_STATUS_LABELS: Record<AgentRunStatus, string> = {
  created: "Created",
  running: "Running",
  waiting_tool: "Waiting for tool",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

function resultTone(status: AgentRunStatus): "pending" | "success" | "error" {
  if (status === "completed") {
    return "success";
  }
  if (status === "failed" || status === "cancelled") {
    return "error";
  }
  return "pending";
}

function runResult(run: AgentRunExecution) {
  const title = run.status === "failed" ? "Run failed" : "Agent run";
  const tone = resultTone(run.status);

  return (
    <article className="agent-run-panel agent-run-panel--result">
      <header className="agent-run-header">
        <div>
          <span className="agent-run-eyebrow">Agent result</span>
          <h2>{title}</h2>
        </div>
        <span className={`agent-run-status agent-run-status--${tone}`}>
          {RUN_STATUS_LABELS[run.status]}
        </span>
      </header>

      <dl className="agent-run-meta">
        <div>
          <dt>Run ID</dt>
          <dd>
            <code className="trace-id">{run.id}</code>
          </dd>
        </div>
        <div>
          <dt>Conversation ID</dt>
          <dd>
            <code className="trace-id">{run.conversation_id}</code>
          </dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>{formatLatency(run.latency_ms)}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>
            <time dateTime={run.created_at}>{run.created_at}</time>
          </dd>
        </div>
      </dl>

      {run.final_answer !== null ? (
        <section className="agent-answer" aria-labelledby="agent-answer-heading">
          <h3 id="agent-answer-heading">Final answer</h3>
          <p>{run.final_answer}</p>
        </section>
      ) : run.error === null ? (
        <p className="agent-answer-empty">Final answer is not available.</p>
      ) : null}

      {run.error !== null ? (
        <p className="agent-run-error" role="alert">
          {run.error}
        </p>
      ) : null}

      <ToolCallTimeline toolCalls={run.tool_calls} />
    </article>
  );
}

type AgentRunPanelProps = {
  state: AgentRunViewState;
};

export default function AgentRunPanel({ state }: AgentRunPanelProps) {
  if (state.status === "result") {
    return runResult(state.run);
  }

  if (state.status === "loading") {
    return (
      <section className="agent-run-panel agent-state" role="status">
        <LoaderCircle size={24} aria-hidden="true" />
        <h2>{state.message}</h2>
        <p>The synchronous run may include one or more read-only ToolCalls.</p>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section className="agent-run-panel agent-state agent-state--error" role="alert">
        <CircleAlert size={24} aria-hidden="true" />
        <h2>Agent request failed</h2>
        <p>{state.message}</p>
        {state.requestId !== null ? (
          <p className="agent-request-id">
            Request ID <code className="trace-id">{state.requestId}</code>
          </p>
        ) : null}
      </section>
    );
  }

  if (state.status === "no-models") {
    return (
      <section className="agent-run-panel agent-state">
        <CircleOff size={24} aria-hidden="true" />
        <h2>No tools-capable model</h2>
        <p>
          Configure a Registry model with <code>supports_tools=true</code> to
          run an Agent task.
        </p>
      </section>
    );
  }

  return (
    <section className="agent-run-panel agent-state">
      <Bot size={24} aria-hidden="true" />
      <h2>Start an Agent task</h2>
      <p>
        Submit a goal to see its final answer and ToolCall audit trail.
      </p>
    </section>
  );
}
