import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createConversation,
  fetchConversationMessages,
  fetchConversations,
} from "./conversations";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("conversation API", () => {
  it("creates a dedicated conversation with exact model defaults", async () => {
    const createdConversation = {
      id: "00000000-0000-0000-0000-000000000409",
      title: "RAG · Engineering notes",
      default_provider: "mock",
      default_model: "mock-model",
      created_at: "2026-08-02T12:00:00",
      updated_at: "2026-08-02T12:00:00",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json(createdConversation, { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const request = {
      title: "RAG · Engineering notes",
      default_provider: "mock",
      default_model: "mock-model",
    };

    await expect(createConversation(request)).resolves.toEqual(
      createdConversation,
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/conversations",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      },
    );
  });

  it("uses a safe structured creation error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json(
          {
            error: {
              code: "validation_error",
              message: "Conversation title is invalid",
              request_id: "request-conversation-1",
            },
          },
          { status: 422 },
        ),
      ),
    );

    await expect(
      createConversation({ title: "Invalid" }),
    ).rejects.toThrow("Conversation title is invalid");
  });

  it("normalizes conversation creation transport failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("private")));

    await expect(
      createConversation({ title: "RAG · Engineering notes" }),
    ).rejects.toThrow("Unable to reach Conversation API");
  });

  it("normalizes invalid conversation creation JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not-json", { status: 201 })),
    );

    await expect(
      createConversation({ title: "RAG · Engineering notes" }),
    ).rejects.toThrow("Conversation API returned invalid JSON");
  });

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
