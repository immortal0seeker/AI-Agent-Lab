import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import AgentTaskForm from "./AgentTaskForm";
import type { ModelOption } from "../../types/models";

const models: ModelOption[] = [
  {
    provider: "provider-a",
    model: "tools-model",
    display_name: "Tools Model",
    supports_streaming: false,
    supports_tools: true,
    supports_json: false,
    input_price_per_1m: null,
    output_price_per_1m: null,
  },
];

function renderForm(
  overrides: Partial<Parameters<typeof AgentTaskForm>[0]> = {},
): string {
  return renderToStaticMarkup(
    <AgentTaskForm
      models={models}
      provider="provider-a"
      model="tools-model"
      input="Read README.md"
      busy={false}
      disabledReason={null}
      hasRun={false}
      onSelectModel={() => undefined}
      onInputChange={() => undefined}
      onSubmit={() => undefined}
      onNewTask={() => undefined}
      {...overrides}
    />,
  );
}

describe("AgentTaskForm", () => {
  it("shows only the caller-provided tools model and enables a valid task", () => {
    const html = renderForm();

    expect(html).toContain("Tools Model - provider-a");
    expect(html).toContain("Read README.md");
    expect(html).toContain("Run Agent");
    expect(html).not.toContain("Cancel");
    expect(html).not.toContain("Retry");
  });

  it("disables submission for blank input", () => {
    const html = renderForm({ input: "   " });

    expect(html).toMatch(/aria-label="Run Agent"[^>]*disabled=""/);
  });

  it("shows a model failure reason and disables submission", () => {
    const html = renderForm({
      models: [],
      provider: null,
      model: null,
      disabledReason: "Unable to load tools-capable models",
    });

    expect(html).toContain("Unable to load tools-capable models");
    expect(html).toMatch(/aria-label="Run Agent"[^>]*disabled=""/);
  });

  it("offers New task only when a run is present", () => {
    expect(renderForm({ hasRun: false })).not.toContain("New task");
    expect(renderForm({ hasRun: true })).toContain("New task");
  });
});
