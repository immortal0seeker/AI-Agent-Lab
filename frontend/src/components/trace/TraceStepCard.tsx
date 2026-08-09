import type { RagRetrievalRun, TraceStep } from "../../types/trace";
import TraceCandidateTable from "./TraceCandidateTable";
import { traceStatusLabel } from "./TraceRunList";


type TraceStepCardProps = {
  step: TraceStep;
  retrieval: RagRetrievalRun | null;
};


export default function TraceStepCard({ step, retrieval }: TraceStepCardProps) {
  return (
    <article className="trace-step-card">
      <header>
        <span className="trace-step-card__index">{step.step_index}</span>
        <div>
          <strong>{step.name}</strong>
          <code>{step.step_type}</code>
        </div>
        <span className={`trace-status trace-status--${step.status}`}>
          {traceStatusLabel(step.status)}
        </span>
      </header>

      <dl className="trace-step-card__metrics">
        <div>
          <dt>Step ID</dt>
          <dd><code>{step.id}</code></dd>
        </div>
        <div>
          <dt>Latency</dt>
          <dd>{step.latency_ms === null ? "—" : `${step.latency_ms} ms`}</dd>
        </div>
      </dl>

      {step.error_message === null ? null : (
        <p className="trace-error" role="alert">{step.error_message}</p>
      )}

      <div className="trace-step-card__metadata">
        <details>
          <summary>Input metadata</summary>
          <pre>{JSON.stringify(step.input_json, null, 2)}</pre>
        </details>
        {step.output_json === null ? null : (
          <details>
            <summary>Output metadata</summary>
            <pre>{JSON.stringify(step.output_json, null, 2)}</pre>
          </details>
        )}
      </div>

      {step.step_type !== "rag_retrieve" ? null : retrieval === null ? (
        <p className="trace-retrieval-missing">
          Retrieval audit is unavailable for this Step
        </p>
      ) : (
        <section className="trace-retrieval" aria-label="Retrieval audit">
          <header>
            <div>
              <span>Retrieval Run</span>
              <code>{retrieval.id}</code>
            </div>
            <div>
              <span>Knowledge Base</span>
              <code>{retrieval.knowledge_base_id}</code>
            </div>
          </header>
          <dl className="trace-retrieval__summary">
            <div><dt>Strategy</dt><dd>{retrieval.strategy_name}</dd></div>
            <div><dt>Top K</dt><dd>{retrieval.top_k}</dd></div>
            <div><dt>Candidates</dt><dd>{retrieval.candidate_count}</dd></div>
            <div><dt>Selected</dt><dd>{retrieval.selected_count}</dd></div>
            <div><dt>Latency</dt><dd>{retrieval.latency_ms} ms</dd></div>
          </dl>
          <TraceCandidateTable retrieval={retrieval} />
        </section>
      )}
    </article>
  );
}
