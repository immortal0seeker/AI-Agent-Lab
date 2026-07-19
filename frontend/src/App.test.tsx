import { afterEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import App from "./App";

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubWindow(search: string) {
  vi.stubGlobal("window", {
    location: {
      search,
      href: `http://localhost:5173/${search}`,
    },
    history: { replaceState: vi.fn() },
  });
}

describe("App workspace selection", () => {
  it("keeps Chat as the default workspace", () => {
    stubWindow("");

    const html = renderToStaticMarkup(<App />);

    expect(html).toContain("<h1>Chat</h1>");
    expect(html).toContain("Streaming workspace");
    expect(html).toContain('aria-label="Workspace"');
  });

  it("restores Agent workspace from the URL", () => {
    stubWindow("?workspace=agent");

    const html = renderToStaticMarkup(<App />);

    expect(html).toContain("<h1>Agent</h1>");
    expect(html).toContain("Read-only ToolCall workspace");
    expect(html).toContain("Loading tools-capable models...");
  });
});
