import { AlertTriangle, CheckCircle2, FileText } from "lucide-react";

import type { KnowledgeDocument } from "../../types/knowledge";

type DocumentStatusCardProps = {
  document: KnowledgeDocument;
};

function statusTone(status: string): "success" | "error" | "pending" {
  if (status === "parsed" || status === "chunked" || status === "ready") {
    return "success";
  }
  return status === "failed" ? "error" : "pending";
}

function statusLabel(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function DocumentStatusCard({
  document,
}: DocumentStatusCardProps) {
  const hasFailure =
    document.parse_status === "failed" ||
    document.chunk_status === "failed" ||
    document.embedding_status === "failed";

  return (
    <section className="document-status-card" aria-labelledby="document-status-heading">
      <header>
        <div className="document-status-title">
          {hasFailure ? (
            <AlertTriangle size={18} aria-hidden="true" />
          ) : (
            <CheckCircle2 size={18} aria-hidden="true" />
          )}
          <div>
            <span className="knowledge-eyebrow">Latest upload</span>
            <h3 id="document-status-heading">{document.original_filename}</h3>
          </div>
        </div>
        <span className={`document-outcome document-outcome--${hasFailure ? "error" : "success"}`}>
          {hasFailure ? "Needs attention" : "Ingested"}
        </span>
      </header>

      <div className="document-lifecycle" aria-label="Document lifecycle">
        <div aria-label={`Parse status: ${document.parse_status}`}>
          <span>Parse</span>
          <strong className={`document-status document-status--${statusTone(document.parse_status)}`}>
            {statusLabel(document.parse_status)}
          </strong>
        </div>
        <div aria-label={`Chunk status: ${document.chunk_status}`}>
          <span>Chunk</span>
          <strong className={`document-status document-status--${statusTone(document.chunk_status)}`}>
            {statusLabel(document.chunk_status)}
          </strong>
        </div>
        <div aria-label={`Embedding status: ${document.embedding_status}`}>
          <span>Embedding</span>
          <strong className={`document-status document-status--${statusTone(document.embedding_status)}`}>
            {statusLabel(document.embedding_status)}
          </strong>
        </div>
      </div>

      {document.error_message ? (
        <p className="document-processing-error" role="alert">
          {document.error_message}
        </p>
      ) : null}

      <dl className="document-meta">
        <div>
          <dt>Document ID</dt>
          <dd>{document.id}</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{document.file_type.toUpperCase()}</dd>
        </div>
        <div>
          <dt>Size</dt>
          <dd>{document.file_size.toLocaleString()} bytes</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>
            <FileText size={13} aria-hidden="true" />
            <time dateTime={document.created_at}>{document.created_at}</time>
          </dd>
        </div>
      </dl>
    </section>
  );
}
