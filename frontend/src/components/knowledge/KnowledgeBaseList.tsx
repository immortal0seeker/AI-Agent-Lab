import { AlertCircle, Database, LoaderCircle, RefreshCw } from "lucide-react";

import type { KnowledgeBase } from "../../types/knowledge";

export type KnowledgeBaseListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: KnowledgeBase[] };

type KnowledgeBaseListProps = {
  state: KnowledgeBaseListState;
  selectedId: string | null;
  disabled: boolean;
  onSelect: (knowledgeBaseId: string) => void;
  onRetry: () => void;
};

export default function KnowledgeBaseList({
  state,
  selectedId,
  disabled,
  onSelect,
  onRetry,
}: KnowledgeBaseListProps) {
  return (
    <section className="knowledge-list-panel" aria-labelledby="knowledge-list-heading">
      <header>
        <div>
          <span className="knowledge-eyebrow">Library</span>
          <h2 id="knowledge-list-heading">Knowledge Bases</h2>
        </div>
        {state.status === "ready" ? (
          <span className="knowledge-count" aria-label={`${state.items.length} Knowledge Bases`}>
            {state.items.length}
          </span>
        ) : null}
      </header>

      {state.status === "loading" ? (
        <div className="knowledge-list-state" role="status" aria-live="polite">
          <LoaderCircle size={18} aria-hidden="true" />
          <span>Loading Knowledge Bases...</span>
        </div>
      ) : state.status === "error" ? (
        <div className="knowledge-list-state knowledge-list-state--error" role="alert">
          <AlertCircle size={18} aria-hidden="true" />
          <span>{state.message}</span>
          <button type="button" disabled={disabled} onClick={onRetry}>
            <RefreshCw size={14} aria-hidden="true" />
            Retry
          </button>
        </div>
      ) : state.items.length === 0 ? (
        <div className="knowledge-list-state">
          <Database size={20} aria-hidden="true" />
          <strong>No Knowledge Bases yet</strong>
          <span>Create one to start ingesting documents.</span>
        </div>
      ) : (
        <ul className="knowledge-base-list">
          {state.items.map((knowledgeBase) => (
            <li key={knowledgeBase.id}>
              <button
                type="button"
                aria-label={`Select ${knowledgeBase.name}`}
                aria-current={selectedId === knowledgeBase.id ? "true" : undefined}
                disabled={disabled}
                onClick={() => onSelect(knowledgeBase.id)}
              >
                <strong>{knowledgeBase.name}</strong>
                <span>{knowledgeBase.description ?? "No description"}</span>
                <code>{knowledgeBase.id}</code>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
