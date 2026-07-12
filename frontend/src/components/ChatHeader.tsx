import { Circle, Radio } from "lucide-react";

import type { ModelOption } from "../types/models";
import ModelSelector from "./ModelSelector";

type ChatHeaderProps = {
  models: ModelOption[];
  provider: string | null;
  model: string | null;
  isStreaming: boolean;
  modelSelectionDisabled: boolean;
  onSelectModel: (provider: string, model: string) => void;
};

export default function ChatHeader({
  models,
  provider,
  model,
  isStreaming,
  modelSelectionDisabled,
  onSelectModel,
}: ChatHeaderProps) {
  return (
    <header className="chat-header">
      <div>
        <h1>Chat</h1>
        <p>Streaming workspace</p>
      </div>
      <div className="model-summary">
        <span className="model-status">
          {isStreaming ? (
            <Radio size={14} aria-hidden="true" />
          ) : (
            <Circle size={9} fill="currentColor" aria-hidden="true" />
          )}
          {isStreaming ? "Streaming" : "Ready"}
        </span>
        <ModelSelector
          models={models}
          provider={provider}
          model={model}
          disabled={modelSelectionDisabled}
          onChange={onSelectModel}
        />
      </div>
    </header>
  );
}
