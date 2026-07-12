import { Circle, Radio } from "lucide-react";

type ChatHeaderProps = {
  provider: string;
  model: string;
  isStreaming: boolean;
};

export default function ChatHeader({
  provider,
  model,
  isStreaming,
}: ChatHeaderProps) {
  return (
    <header className="chat-header">
      <div>
        <h1>Chat</h1>
        <p>Streaming workspace</p>
      </div>
      <div className="model-summary" aria-label="Current model configuration">
        <span className="model-status">
          {isStreaming ? (
            <Radio size={14} aria-hidden="true" />
          ) : (
            <Circle size={9} fill="currentColor" aria-hidden="true" />
          )}
          {isStreaming ? "Streaming" : "Ready"}
        </span>
        <span className="model-identity" title={`${provider} / ${model}`}>
          <strong>{model}</strong>
          <span>{provider}</span>
        </span>
      </div>
    </header>
  );
}
