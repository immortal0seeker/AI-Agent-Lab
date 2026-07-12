import { afterEach, describe, expect, it, vi } from "vitest";

import { createApiUrl, getJson } from "./client";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("createApiUrl", () => {
  it("joins a base URL and API path consistently", () => {
    expect(createApiUrl("http://localhost:8000/api/v1/", "health")).toBe(
      "http://localhost:8000/api/v1/health",
    );
  });

  it("preserves paths that already start with a slash", () => {
    expect(createApiUrl("http://localhost:8000/api/v1", "/health")).toBe(
      "http://localhost:8000/api/v1/health",
    );
  });

  it("uses backend detail for JSON request failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Conversation missing" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(getJson("/conversations/missing")).rejects.toThrow(
      "Conversation missing",
    );
  });

  it("falls back to the response status for non-JSON failures", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("bad gateway", { status: 502 })),
    );

    await expect(getJson("/models")).rejects.toThrow(
      "Request failed with status 502",
    );
  });
});
