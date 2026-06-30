import { describe, expect, it } from "vitest";

import { createApiUrl } from "./client";

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
});
