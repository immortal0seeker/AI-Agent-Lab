import { Send, Square } from "lucide-react";
import { type FormEvent, type KeyboardEvent, useState } from "react";

type MessageComposerProps = {
  isStreaming: boolean;
  onSend: (content: string) => Promise<void>;
  onStop: () => void;
};

export default function MessageComposer({
  isStreaming,
  onSend,
  onStop,
}: MessageComposerProps) {
  const [content, setContent] = useState("");
  const canSend = content.trim().length > 0 && !isStreaming;

  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const nextContent = content.trim();
    if (!nextContent || isStreaming) {
      return;
    }
    setContent("");
    void onSend(nextContent);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        aria-label="Message"
        placeholder="Message the configured model"
        rows={2}
        value={content}
        disabled={isStreaming}
        onChange={(event) => setContent(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      {isStreaming ? (
        <button
          className="composer-action composer-action--stop"
          type="button"
          title="Stop generation"
          aria-label="Stop generation"
          onClick={onStop}
        >
          <Square size={16} fill="currentColor" aria-hidden="true" />
        </button>
      ) : (
        <button
          className="composer-action composer-action--send"
          type="submit"
          title="Send message"
          aria-label="Send message"
          disabled={!canSend}
        >
          <Send size={17} aria-hidden="true" />
        </button>
      )}
    </form>
  );
}
