import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchHealth } from "./health";

describe("fetchHealth", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads the backend health payload from the health endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        status: "ok",
        service: "ai-agent-lab-backend",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchHealth()).resolves.toEqual({
      status: "ok",
      service: "ai-agent-lab-backend",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/health",
    );
  });
});
