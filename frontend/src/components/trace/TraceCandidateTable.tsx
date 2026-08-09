import type {
  RagRetrievalCandidate,
  RagRetrievalRun,
} from "../../types/trace";


type TraceCandidateTableProps = {
  retrieval: RagRetrievalRun;
};

function candidateScores(candidate: RagRetrievalCandidate) {
  return [
    ["dense_score", candidate.dense_score],
    ["sparse_score", candidate.sparse_score],
    ["fused_score", candidate.fused_score],
    ["rerank_score", candidate.rerank_score],
  ].filter((entry): entry is [string, number] => entry[1] !== null);
}

export default function TraceCandidateTable({
  retrieval,
}: TraceCandidateTableProps) {
  if (retrieval.candidates.length === 0) {
    return (
      <div className="trace-candidate-empty" role="status">
        No retrieval candidates recorded
      </div>
    );
  }

  const candidates = [...retrieval.candidates].sort(
    (left, right) => left.rank - right.rank || left.id.localeCompare(right.id),
  );

  return (
    <div className="trace-candidate-table" role="table" aria-label="Retrieval candidates">
      {candidates.map((candidate) => (
        <article key={candidate.id} className="trace-candidate-row" role="row">
          <div className="trace-candidate-row__heading">
            <strong>Rank {candidate.rank}</strong>
            <span>{candidate.source}</span>
            <span>{candidate.selected ? "Selected" : "Not selected"}</span>
          </div>
          <p>{candidate.content_preview}</p>
          <dl className="trace-candidate-row__scores">
            {candidateScores(candidate).map(([name, value]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
          <dl className="trace-id-grid">
            <div>
              <dt>Candidate ID</dt>
              <dd><code>{candidate.id}</code></dd>
            </div>
            <div>
              <dt>Document ID</dt>
              <dd><code>{candidate.document_id}</code></dd>
            </div>
            <div>
              <dt>Chunk ID</dt>
              <dd><code>{candidate.chunk_id}</code></dd>
            </div>
          </dl>
          {Object.keys(candidate.metadata_json).length === 0 ? null : (
            <details>
              <summary>Candidate metadata</summary>
              <pre>{JSON.stringify(candidate.metadata_json, null, 2)}</pre>
            </details>
          )}
        </article>
      ))}
    </div>
  );
}
