import type { ModelOption } from "../types/models";

type ModelSelectorProps = {
  models: ModelOption[];
  provider: string | null;
  model: string | null;
  disabled: boolean;
  onChange: (provider: string, model: string) => void;
};

function modelKey(provider: string, model: string): string {
  return JSON.stringify([provider, model]);
}

export default function ModelSelector({
  models,
  provider,
  model,
  disabled,
  onChange,
}: ModelSelectorProps) {
  const value =
    provider !== null && model !== null ? modelKey(provider, model) : "";

  return (
    <label className="model-selector">
      <span>Model</span>
      <select
        aria-label="Model"
        value={value}
        disabled={disabled || models.length === 0}
        onChange={(event) => {
          const selected = models.find(
            (option) =>
              modelKey(option.provider, option.model) === event.target.value,
          );
          if (selected !== undefined) {
            onChange(selected.provider, selected.model);
          }
        }}
      >
        {models.length === 0 ? <option value="">No models configured</option> : null}
        {models.map((option) => (
          <option
            key={modelKey(option.provider, option.model)}
            value={modelKey(option.provider, option.model)}
          >
            {option.display_name} - {option.provider}
          </option>
        ))}
      </select>
    </label>
  );
}
