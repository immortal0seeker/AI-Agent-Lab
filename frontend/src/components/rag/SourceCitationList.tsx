import type { RagSource } from "../../types/rag";
import RagSourceCard from "./RagSourceCard";

type SourceCitationListProps = {
  sources: RagSource[];
};

export default function SourceCitationList({
  sources,
}: SourceCitationListProps) {
  return (
    <section className="rag-source-list" aria-labelledby="rag-sources-heading">
      <header>
        <h4 id="rag-sources-heading">Sources</h4>
        <span>{sources.length}</span>
      </header>
      {sources.length === 0 ? (
        <div className="rag-source-empty">No sources were used</div>
      ) : (
        <div className="rag-source-grid">
          {sources.map((source) => (
            <RagSourceCard
              key={`${source.source_index}:${source.chunk_id}`}
              source={source}
            />
          ))}
        </div>
      )}
    </section>
  );
}
