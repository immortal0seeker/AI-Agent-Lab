import type { ToolCall } from "../../types/agent";
import ToolCallCard from "./ToolCallCard";

type ToolCallTimelineProps = {
  toolCalls: ToolCall[];
};

export default function ToolCallTimeline({
  toolCalls,
}: ToolCallTimelineProps) {
  if (toolCalls.length === 0) {
    return (
      <section className="tool-call-timeline" aria-labelledby="tool-calls-heading">
        <h3 id="tool-calls-heading">Tool calls</h3>
        <p className="tool-call-empty">This run did not call any tools.</p>
      </section>
    );
  }

  return (
    <section className="tool-call-timeline" aria-labelledby="tool-calls-heading">
      <div className="tool-call-timeline__heading">
        <h3 id="tool-calls-heading">Tool calls</h3>
        <span>{toolCalls.length}</span>
      </div>
      <ol>
        {toolCalls.map((toolCall) => (
          <li key={toolCall.id}>
            <ToolCallCard toolCall={toolCall} />
          </li>
        ))}
      </ol>
    </section>
  );
}
