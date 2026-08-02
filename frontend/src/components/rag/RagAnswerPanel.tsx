import type { RagTurn } from "../../types/rag";
import SourceCitationList from "./SourceCitationList";

type RagAnswerPanelProps = {
  turn: RagTurn;
};

export default function RagAnswerPanel({ turn }: RagAnswerPanelProps) {
  return (
    <article className="rag-answer-panel" aria-label={`RAG answer ${turn.rag_query_id}`}>
      <section className="rag-answer-question">
        <span>You</span>
        <p>{turn.query}</p>
      </section>

      <section className="rag-answer-content">
        <span>Grounded answer</span>
        <p>{turn.answer}</p>
      </section>

      <div className="rag-answer-summary" aria-label="Retrieval summary">
        <span>{turn.metadata.strategy}</span>
        <span>Top-K {turn.metadata.top_k}</span>
        <span>{turn.metadata.result_count} retrieved</span>
        <span>{turn.metadata.used_source_count} used</span>
        <span>{turn.metadata.context_characters} context characters</span>
        <span>{turn.provider} / {turn.model}</span>
        <span>
          {turn.usage === null
            ? "Usage unavailable"
            : `${turn.usage.total_tokens} tokens`}
        </span>
      </div>

      <dl className="rag-answer-audit">
        <div>
          <dt>RAG Query ID</dt>
          <dd>{turn.rag_query_id}</dd>
        </div>
        <div>
          <dt>LLM Call ID</dt>
          <dd>{turn.llm_call_id}</dd>
        </div>
        <div>
          <dt>Conversation ID</dt>
          <dd>{turn.conversation_id}</dd>
        </div>
      </dl>

      <SourceCitationList sources={turn.sources} />
    </article>
  );
}
