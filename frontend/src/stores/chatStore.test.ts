import { describe, expect, it } from "vitest";

import { createChatStore, type StreamChatFunction } from "./chatStore";
import type { ChatCompletionResponse } from "../types/chat";

function createDoneResponse(content = "Complete answer"): ChatCompletionResponse {
  return {
    conversation_id: "conversation-1",
    user_message: {
      id: "user-1",
      conversation_id: "conversation-1",
      role: "user",
      content: "Hello",
      model: null,
      provider: null,
      created_at: "2026-07-12T12:00:00",
    },
    assistant_message: {
      id: "assistant-1",
      conversation_id: "conversation-1",
      role: "assistant",
      content,
      model: "example-model",
      provider: "openai_compatible",
      created_at: "2026-07-12T12:00:01",
    },
    provider: "openai_compatible",
    model: "example-model",
    usage: null,
    llm_call_id: "call-1",
  };
}

describe("chat store", () => {
  it("streams deltas and replaces temporary messages with persisted messages", async () => {
    const streamer: StreamChatFunction = async (_request, options) => {
      options.onDelta("Complete ");
      options.onDelta("answer");
      return createDoneResponse();
    };
    const store = createChatStore(streamer);

    await store.getState().sendMessage("Hello");

    expect(store.getState().status).toBe("idle");
    expect(store.getState().conversationId).toBe("conversation-1");
    expect(store.getState().messages).toEqual([
      { id: "user-1", role: "user", content: "Hello", status: "complete" },
      {
        id: "assistant-1",
        role: "assistant",
        content: "Complete answer",
        status: "complete",
      },
    ]);
  });

  it("preserves partial output and exposes a readable stream error", async () => {
    const streamer: StreamChatFunction = async (_request, options) => {
      options.onDelta("Partial answer");
      throw new Error("Provider unavailable");
    };
    const store = createChatStore(streamer);

    await store.getState().sendMessage("Hello");

    expect(store.getState().status).toBe("error");
    expect(store.getState().error).toBe("Provider unavailable");
    expect(store.getState().messages.at(-1)).toMatchObject({
      role: "assistant",
      content: "Partial answer",
      status: "error",
    });
  });

  it("stops an active request and keeps its partial assistant text", async () => {
    const streamer: StreamChatFunction = (_request, options) =>
      new Promise((_resolve, reject) => {
        options.onDelta("Partial answer");
        options.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    const store = createChatStore(streamer);

    const pending = store.getState().sendMessage("Hello");
    await Promise.resolve();
    store.getState().stopGeneration();
    await pending;

    expect(store.getState().status).toBe("idle");
    expect(store.getState().messages.at(-1)).toMatchObject({
      content: "Partial answer",
      status: "stopped",
    });
  });

  it("ignores late stream callbacks after starting a new chat", async () => {
    let finish: ((response: ChatCompletionResponse) => void) | undefined;
    let sendDelta: ((content: string) => void) | undefined;
    const streamer: StreamChatFunction = (_request, options) => {
      sendDelta = options.onDelta;
      return new Promise((resolve) => {
        finish = resolve;
      });
    };
    const store = createChatStore(streamer);

    const pending = store.getState().sendMessage("Hello");
    await Promise.resolve();
    store.getState().newChat();
    sendDelta?.("late delta");
    finish?.(createDoneResponse("late answer"));
    await pending;

    expect(store.getState().conversationId).toBeNull();
    expect(store.getState().messages).toEqual([]);
    expect(store.getState().status).toBe("idle");
  });
});
