import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchConversationMessages,
  fetchConversations,
} from "./conversations";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("conversation API", () => {
  it("loads conversation summaries", async () => {
    const conversations = [
      {
        id: "conversation-1",
        title: "Recent conversation",
        default_provider: "openai_compatible",
        default_model: "example-model",
        created_at: "2026-07-12T12:00:00",
        updated_at: "2026-07-12T12:01:00",
      },
    ];
    const fetchMock = vi
      .fn()
      .mockResolvedValue(Response.json(conversations, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchConversations()).resolves.toEqual(conversations);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/conversations",
    );
  });

  it("loads ordered messages for one encoded conversation ID", async () => {
    const messages = [
      {
        id: "message-1",
        conversation_id: "conversation/1",
        role: "user",
        content: "Persisted question",
        model: null,
        provider: null,
        created_at: "2026-07-12T12:00:00",
      },
    ];
    const fetchMock = vi
      .fn()
      .mockResolvedValue(Response.json(messages, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchConversationMessages("conversation/1")).resolves.toEqual(
      messages,
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/conversations/conversation%2F1/messages",
    );
  });
});
