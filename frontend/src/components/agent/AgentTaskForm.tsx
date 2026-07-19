import { Play, Plus } from "lucide-react";
import { type FormEvent } from "react";

import type { ModelOption } from "../../types/models";
import ModelSelector from "../ModelSelector";

type AgentTaskFormProps = {
  models: ModelOption[];
  provider: string | null;
  model: string | null;
  input: string;
  busy: boolean;
  disabledReason: string | null;
  hasRun: boolean;
  onSelectModel: (provider: string, model: string) => void;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  onNewTask: () => void;
};

export default function AgentTaskForm({
  models,
  provider,
  model,
  input,
  busy,
  disabledReason,
  hasRun,
  onSelectModel,
  onInputChange,
  onSubmit,
  onNewTask,
}: AgentTaskFormProps) {
  const canSubmit =
    input.trim().length > 0 &&
    provider !== null &&
    model !== null &&
    !busy &&
    disabledReason === null;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (canSubmit) {
      onSubmit();
    }
  };

  return (
    <form className="agent-task-form" onSubmit={submit}>
      <div className="agent-task-form__heading">
        <div>
          <h2>Agent task</h2>
          <p>Use read-only workspace tools and return an auditable result.</p>
        </div>
        <ModelSelector
          models={models}
          provider={provider}
          model={model}
          disabled={busy || disabledReason !== null}
          onChange={onSelectModel}
        />
      </div>

      <label className="agent-task-input">
        <span>Task</span>
        <textarea
          aria-label="Agent task"
          placeholder="Read README.md and summarize the project structure"
          rows={4}
          value={input}
          disabled={busy || disabledReason !== null}
          onChange={(event) => onInputChange(event.target.value)}
        />
      </label>

      {disabledReason !== null ? (
        <p className="agent-disabled-reason" role="status">
          {disabledReason}
        </p>
      ) : null}

      <div className="agent-actions">
        {hasRun ? (
          <button
            className="agent-secondary-action"
            type="button"
            disabled={busy}
            onClick={onNewTask}
          >
            <Plus size={15} aria-hidden="true" />
            New task
          </button>
        ) : null}
        <button
          className="agent-primary-action"
          type="submit"
          aria-label="Run Agent"
          disabled={!canSubmit}
        >
          <Play size={15} fill="currentColor" aria-hidden="true" />
          {busy ? "Running..." : "Run Agent"}
        </button>
      </div>
    </form>
  );
}
