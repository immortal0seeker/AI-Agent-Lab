import type { ToolCall, ToolCallStatus } from "../../types/agent";
import {
  formatJson,
  formatLatency,
  summarizeText,
  toolCallTone,
  toolResultSections,
} from "./toolCallView";

const STATUS_LABELS: Record<ToolCallStatus, string> = {
  pending: "Pending",
  running: "Running",
  success: "Success",
  failed: "Failed",
  timeout: "Timeout",
  blocked: "Blocked",
};

type ToolCallCardProps = {
  toolCall: ToolCall;
};

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const tone = toolCallTone(toolCall.status);
  const resultSections =
    toolCall.result === null
      ? []
      : toolResultSections(toolCall.result).filter(
          (section) => section.tone !== "error",
        );
  const visibleError =
    toolCall.error ??
    (toolCall.result?.success === false ? toolCall.result.error : null);

  return (
    <article className="tool-call-card" aria-label={`${toolCall.tool_name} ToolCall`}>
      <header className="tool-call-card__header">
        <div>
          <span className="tool-call-card__eyebrow">Tool</span>
          <h4>{toolCall.tool_name}</h4>
        </div>
        <span
          className={`tool-call-status tool-call-status--${tone}`}
          data-status={toolCall.status}
        >
          {STATUS_LABELS[toolCall.status]}
        </span>
      </header>

      <dl className="tool-call-grid">
        <div>
          <dt>Latency</dt>
          <dd>{formatLatency(toolCall.latency_ms)}</dd>
        </div>
        <div>
          <dt>Sequence</dt>
          <dd>{toolCall.sequence_index}</dd>
        </div>
        <div>
          <dt>Tool Call ID</dt>
          <dd>
            <code className="trace-id">{toolCall.tool_call_id}</code>
          </dd>
        </div>
        <div>
          <dt>Database ID</dt>
          <dd>
            <code className="trace-id">{toolCall.id}</code>
          </dd>
        </div>
      </dl>

      <section className="tool-call-section">
        <h5>Arguments</h5>
        <pre className="tool-call-json">
          {summarizeText(formatJson(toolCall.arguments))}
        </pre>
      </section>

      {visibleError !== null ? (
        <p className="tool-call-error" role="alert">
          {visibleError}
        </p>
      ) : null}

      {resultSections.length > 0 ? (
        <section className="tool-call-result" aria-label="Tool result summary">
          {resultSections.map((section) => (
            <div key={section.label}>
              <h5>{section.label}</h5>
              <pre className="tool-call-json">{section.value}</pre>
            </div>
          ))}
        </section>
      ) : toolCall.result === null ? (
        <p className="tool-call-pending">Result not available yet.</p>
      ) : null}
    </article>
  );
}
