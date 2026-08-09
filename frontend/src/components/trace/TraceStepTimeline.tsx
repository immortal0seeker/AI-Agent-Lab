import type {
  RagRetrievalRun,
  TraceRunDetail,
  TraceStep,
} from "../../types/trace";
import TraceStepCard from "./TraceStepCard";


export function retrievalRunIdForStep(step: TraceStep): string | null {
  const candidate = step.output_json?.retrieval_run_id;
  return typeof candidate === "string" ? candidate : null;
}

export function retrievalForStep(
  step: TraceStep,
  retrievalRuns: RagRetrievalRun[],
): RagRetrievalRun | null {
  const id = retrievalRunIdForStep(step);
  return id === null
    ? null
    : (retrievalRuns.find((item) => item.id === id) ?? null);
}

type TraceStepTimelineProps = {
  detail: TraceRunDetail;
};


export default function TraceStepTimeline({ detail }: TraceStepTimelineProps) {
  const steps = [...detail.steps].sort(
    (left, right) =>
      left.step_index - right.step_index || left.id.localeCompare(right.id),
  );

  if (steps.length === 0) {
    return <div className="trace-step-empty">No Trace Steps recorded</div>;
  }

  return (
    <section className="trace-step-timeline" aria-labelledby="trace-steps-heading">
      <h3 id="trace-steps-heading">Step Timeline</h3>
      <div className="trace-step-timeline__items">
        {steps.map((step) => (
          <TraceStepCard
            key={step.id}
            step={step}
            retrieval={retrievalForStep(step, detail.retrieval_runs)}
          />
        ))}
      </div>
    </section>
  );
}
