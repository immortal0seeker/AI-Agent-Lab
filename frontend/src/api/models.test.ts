import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchModels } from "./models";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("fetchModels", () => {
  it("loads Registry models from the API", async () => {
    const models = [
      {
        provider: "openai_compatible",
        model: "example-model",
        display_name: "Example Model",
        supports_streaming: true,
        supports_tools: false,
        supports_json: false,
        input_price_per_1m: null,
        output_price_per_1m: null,
      },
    ];
    const fetchMock = vi
      .fn()
      .mockResolvedValue(Response.json(models, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchModels()).resolves.toEqual(models);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/models",
    );
  });
});
