import { LoaderCircle, Send } from "lucide-react";
import { type FormEvent, useState } from "react";

type RagComposerProps = {
  busy: boolean;
  disabled: boolean;
  error: string | null;
  onSend: (query: string) => Promise<boolean>;
};

export default function RagComposer({
  busy,
  disabled,
  error,
  onSend,
}: RagComposerProps) {
  const [query, setQuery] = useState("");
  const canSend = query.trim().length > 0 && !busy && !disabled;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery || busy || disabled) {
      return;
    }
    if (await onSend(trimmedQuery)) {
      setQuery("");
    }
  };

  return (
    <form
      className="rag-composer"
      aria-label="Ask Knowledge Base"
      aria-busy={busy}
      onSubmit={(event) => void submit(event)}
    >
      <label>
        <span>Question</span>
        <textarea
          aria-label="RAG question"
          placeholder="Ask using this Knowledge Base"
          rows={3}
          value={query}
          disabled={busy || disabled}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      {error ? (
        <p className="knowledge-form-error" role="alert">
          {error}
        </p>
      ) : null}
      <button type="submit" disabled={!canSend}>
        {busy ? (
          <LoaderCircle size={15} aria-hidden="true" />
        ) : (
          <Send size={15} aria-hidden="true" />
        )}
        {busy ? "Asking..." : "Ask"}
      </button>
    </form>
  );
}
