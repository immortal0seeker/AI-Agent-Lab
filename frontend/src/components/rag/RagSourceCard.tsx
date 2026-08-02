import type { JsonValue, RagSource } from "../../types/rag";

type RagSourceCardProps = {
  source: RagSource;
};

function normalizeJson(value: JsonValue): JsonValue {
  if (Array.isArray(value)) {
    return value.map(normalizeJson);
  }
  if (typeof value === "object" && value !== null) {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, nested]) => [key, normalizeJson(nested)]),
    );
  }
  return value;
}

function formatMetadata(value: JsonValue): string {
  const formatted =
    typeof value === "string"
      ? value
      : JSON.stringify(normalizeJson(value));
  return formatted.length > 2_000
    ? `${formatted.slice(0, 1_999)}…`
    : formatted;
}

export default function RagSourceCard({ source }: RagSourceCardProps) {
  const metadata = Object.entries(source.metadata).sort(([left], [right]) =>
    left.localeCompare(right),
  );

  return (
    <article
      className="rag-source-card"
      aria-label={`Source ${source.source_index}: ${source.filename}`}
    >
      <header>
        <div>
          <span className="rag-source-index">[{source.source_index}]</span>
          <strong>{source.filename}</strong>
        </div>
        <span className="rag-source-score" aria-label={`Similarity score ${source.score}`}>
          {source.score.toFixed(4)}
        </span>
      </header>

      <p className="rag-source-content">{source.content}</p>

      <div className="rag-source-location">
        <span>Chunk {source.chunk_index}</span>
        {source.heading ? <span>Heading: {source.heading}</span> : null}
        {source.page_number ? <span>Page {source.page_number}</span> : null}
      </div>

      <dl className="rag-source-provenance">
        <div>
          <dt>Document ID</dt>
          <dd>{source.document_id}</dd>
        </div>
        <div>
          <dt>Chunk ID</dt>
          <dd>{source.chunk_id}</dd>
        </div>
        <div>
          <dt>Embedding</dt>
          <dd>{source.embedding_provider} / {source.embedding_model}</dd>
        </div>
      </dl>

      <section className="rag-source-metadata" aria-label={`Source ${source.source_index} metadata`}>
        <h5>Metadata</h5>
        {metadata.length === 0 ? (
          <p>No metadata</p>
        ) : (
          <dl>
            {metadata.map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>{formatMetadata(value)}</dd>
              </div>
            ))}
          </dl>
        )}
      </section>
    </article>
  );
}
