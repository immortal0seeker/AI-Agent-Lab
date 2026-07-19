import { afterEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

import ChatPage from "./ChatPage";

const storeHarness = vi.hoisted(() => ({
  overrides: {} as Record<string, unknown>,
}));

vi.mock("../stores/chatStore", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../stores/chatStore")>();
  const initialState = actual.useChatStore.getState();

  return {
    ...actual,
    useChatStore: <T,>(selector: (state: typeof initialState) => T): T =>
      selector({ ...initialState, ...storeHarness.overrides }),
  };
});

afterEach(() => {
  storeHarness.overrides = {};
});

describe("ChatPage workspace states", () => {
  it("shows initialization loading instead of the ready empty state", () => {
    storeHarness.overrides = {
      workspaceStatus: "loading",
      workspaceError: null,
      messages: [],
    };

    const html = renderToStaticMarkup(
      <ChatPage onSelectWorkspace={() => undefined} />,
    );

    expect(html).toContain("Loading Chat workspace...");
    expect(html).toContain(">Loading<");
    expect(html).not.toContain(">Ready<");
    expect(html).not.toContain("Start a conversation");
  });

  it("shows one initialization error with a retry action", () => {
    const message = "Unable to initialize Chat workspace";
    storeHarness.overrides = {
      workspaceStatus: "error",
      workspaceError: message,
      messages: [],
    };

    const html = renderToStaticMarkup(
      <ChatPage onSelectWorkspace={() => undefined} />,
    );

    expect(html.match(new RegExp(message, "g"))).toHaveLength(1);
    expect(html).toContain(">Retry<");
    expect(html).toContain(">Unavailable<");
    expect(html).not.toContain(">Ready<");
    expect(html).not.toContain("Start a conversation");
  });

  it("shows Chat and Agent workspace navigation without changing Chat content", () => {
    storeHarness.overrides = {
      workspaceStatus: "ready",
      workspaceError: null,
      messages: [],
    };

    const html = renderToStaticMarkup(
      <ChatPage onSelectWorkspace={() => undefined} />,
    );

    expect(html).toContain("Chat workspace");
    expect(html).toContain("Agent workspace");
    expect(html).toContain('aria-current="page"');
    expect(html).toContain("Start a conversation");
  });
});
