import { Circle, Radio } from "lucide-react";

import type { ModelOption } from "../types/models";
import ModelSelector from "./ModelSelector";

type ChatHeaderProps = {
  models: ModelOption[];
  provider: string | null;
  model: string | null;
  workspaceStatus: "idle" | "loading" | "ready" | "error";
  isStreaming: boolean;
  modelSelectionDisabled: boolean;
  onSelectModel: (provider: string, model: string) => void;
};

export default function ChatHeader({
  models,
  provider,
  model,
  workspaceStatus,
  isStreaming,
  modelSelectionDisabled,
  onSelectModel,
}: ChatHeaderProps) {
  const modelStatus = isStreaming
    ? "streaming"
    : workspaceStatus === "ready"
      ? "ready"
      : workspaceStatus === "error"
        ? "unavailable"
        : "loading";
  const modelStatusLabel =
    modelStatus === "streaming"
      ? "Streaming"
      : modelStatus === "ready"
        ? "Ready"
        : modelStatus === "unavailable"
          ? "Unavailable"
          : "Loading";

  return (
    <header className="chat-header">
      <div>
        <h1>Chat</h1>
        <p>Streaming workspace</p>
      </div>
      <div className="model-summary">
        <span className={`model-status model-status--${modelStatus}`}>
          {isStreaming ? (
            <Radio size={14} aria-hidden="true" />
          ) : (
            <Circle size={9} fill="currentColor" aria-hidden="true" />
          )}
          {modelStatusLabel}
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
