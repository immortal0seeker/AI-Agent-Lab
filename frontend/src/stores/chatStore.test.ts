import { describe, expect, it } from "vitest";

import {
  createChatStore,
  type ChatStoreDependencies,
  type StreamChatFunction,
} from "./chatStore";
import type { ApiMessage, ChatCompletionResponse } from "../types/chat";
import type { ConversationSummary } from "../types/conversations";
import type { ModelOption } from "../types/models";

const models: ModelOption[] = [
  {
    provider: "provider-a",
    model: "model-a",
    display_name: "Model A",
    supports_streaming: true,
    supports_tools: false,
    supports_json: false,
    input_price_per_1m: null,
    output_price_per_1m: null,
  },
  {
    provider: "provider-b",
    model: "model-b",
    display_name: "Model B",
    supports_streaming: true,
    supports_tools: false,
    supports_json: false,
    input_price_per_1m: null,
    output_price_per_1m: null,
  },
];

const conversations: ConversationSummary[] = [
  {
    id: "conversation-2",
    title: "Recent conversation",
    default_provider: "provider-b",
    default_model: "model-b",
    created_at: "2026-07-12T12:00:00",
    updated_at: "2026-07-12T12:02:00",
  },
  {
    id: "conversation-1",
    title: "Older conversation",
    default_provider: "provider-a",
    default_model: "model-a",
    created_at: "2026-07-12T11:00:00",
    updated_at: "2026-07-12T12:01:00",
  },
];

const persistedMessages: ApiMessage[] = [
  {
    id: "persisted-user",
    conversation_id: "conversation-2",
    role: "user",
    content: "Persisted question",
    model: null,
    provider: null,
    created_at: "2026-07-12T12:00:00",
  },
  {
    id: "persisted-assistant",
    conversation_id: "conversation-2",
    role: "assistant",
    content: "Persisted answer",
    model: "model-b",
    provider: "provider-b",
    created_at: "2026-07-12T12:00:01",
  },
];

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

function createWorkspaceDependencies(
  overrides: Partial<ChatStoreDependencies> = {},
): ChatStoreDependencies {
  return {
    streamChat: async () => createDoneResponse(),
    fetchModels: async () => models,
    fetchConversations: async () => conversations,
    fetchConversationMessages: async () => persistedMessages,
    defaultProvider: "provider-a",
    defaultModel: "model-a",
    ...overrides,
  };
}

describe("chat store", () => {
  it("streams deltas and replaces temporary messages with persisted messages", async () => {
    const streamer: StreamChatFunction = async (_request, options) => {
      options.onDelta("Complete ");
      options.onDelta("answer");
      return createDoneResponse();
    };
    const store = createChatStore(
      createWorkspaceDependencies({ streamChat: streamer }),
    );

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
    const store = createChatStore(
      createWorkspaceDependencies({ streamChat: streamer }),
    );

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
    const store = createChatStore(
      createWorkspaceDependencies({ streamChat: streamer }),
    );

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
    const store = createChatStore(
      createWorkspaceDependencies({ streamChat: streamer }),
    );

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

  it("initializes models and conversations with the configured default", async () => {
    const store = createChatStore(createWorkspaceDependencies());

    await store.getState().initialize(null);

    expect(store.getState()).toMatchObject({
      models,
      conversations,
      selectedProvider: "provider-a",
      selectedModel: "model-a",
      workspaceStatus: "ready",
    });
  });

  it("retries initialization after a failed attempt", async () => {
    let modelCalls = 0;
    const store = createChatStore(
      createWorkspaceDependencies({
        fetchModels: async () => {
          modelCalls += 1;
          if (modelCalls === 1) {
            throw new Error("Registry temporarily unavailable");
          }
          return models;
        },
      }),
    );

    await store.getState().initialize(null);
    expect(store.getState()).toMatchObject({
      workspaceStatus: "error",
      workspaceError: "Registry temporarily unavailable",
    });

    await store.getState().initialize(null);
    expect(store.getState()).toMatchObject({
      models,
      conversations,
      selectedProvider: "provider-a",
      selectedModel: "model-a",
      workspaceStatus: "ready",
      workspaceError: null,
    });
    expect(modelCalls).toBe(2);
  });

  it("falls back to the first Registry model", async () => {
    const store = createChatStore(
      createWorkspaceDependencies({
        defaultProvider: "missing-provider",
        defaultModel: "missing-model",
      }),
    );

    await store.getState().initialize(null);

    expect(store.getState().selectedProvider).toBe("provider-a");
    expect(store.getState().selectedModel).toBe("model-a");
  });

  it("restores URL conversation messages and its saved model", async () => {
    const store = createChatStore(createWorkspaceDependencies());

    await store.getState().initialize("conversation-2");

    expect(store.getState().conversationId).toBe("conversation-2");
    expect(store.getState().selectedProvider).toBe("provider-b");
    expect(store.getState().selectedModel).toBe("model-b");
    expect(store.getState().messages).toEqual([
      {
        id: "persisted-user",
        role: "user",
        content: "Persisted question",
        status: "complete",
      },
      {
        id: "persisted-assistant",
        role: "assistant",
        content: "Persisted answer",
        status: "complete",
      },
    ]);
  });

  it("stays initializing until URL conversation messages are restored", async () => {
    let finishMessages: ((messages: ApiMessage[]) => void) | undefined;
    const store = createChatStore(
      createWorkspaceDependencies({
        fetchConversationMessages: () =>
          new Promise((resolve) => {
            finishMessages = resolve;
          }),
      }),
    );

    const initialization = store.getState().initialize("conversation-2");
    await Promise.resolve();
    await Promise.resolve();

    expect(store.getState().workspaceStatus).toBe("loading");
    finishMessages?.(persistedMessages);
    await initialization;
    expect(store.getState().workspaceStatus).toBe("ready");
  });

  it("does not restore the URL conversation after New Chat during initialization", async () => {
    let finishModels: ((models: ModelOption[]) => void) | undefined;
    const store = createChatStore(
      createWorkspaceDependencies({
        fetchModels: () =>
          new Promise((resolve) => {
            finishModels = resolve;
          }),
      }),
    );

    const initialization = store.getState().initialize("conversation-2");
    await Promise.resolve();
    store.getState().newChat();
    finishModels?.(models);
    await initialization;

    expect(store.getState().workspaceStatus).toBe("ready");
    expect(store.getState().conversationId).toBeNull();
    expect(store.getState().messages).toEqual([]);
  });

  it("uses a newly selected model for the next Chat request", async () => {
    let receivedProvider = "";
    let receivedModel = "";
    const store = createChatStore(
      createWorkspaceDependencies({
        streamChat: async (request) => {
          receivedProvider = request.provider;
          receivedModel = request.model;
          return createDoneResponse();
        },
      }),
    );
    await store.getState().initialize(null);

    store.getState().selectModel("provider-b", "model-b");
    await store.getState().sendMessage("Hello");

    expect(receivedProvider).toBe("provider-b");
    expect(receivedModel).toBe("model-b");
  });

  it("ignores a stale history response after a newer selection", async () => {
    const resolvers = new Map<string, (messages: ApiMessage[]) => void>();
    const store = createChatStore(
      createWorkspaceDependencies({
        fetchConversationMessages: (conversationId) =>
          new Promise((resolve) => resolvers.set(conversationId, resolve)),
      }),
    );
    await store.getState().initialize(null);

    const olderSelection = store.getState().selectConversation("conversation-1");
    const newerSelection = store.getState().selectConversation("conversation-2");
    resolvers.get("conversation-2")?.(persistedMessages);
    await newerSelection;
    resolvers.get("conversation-1")?.([
      { ...persistedMessages[0], content: "Stale question" },
    ]);
    await olderSelection;

    expect(store.getState().conversationId).toBe("conversation-2");
    expect(store.getState().messages[0].content).toBe("Persisted question");
  });

  it("starts a new Chat without resetting the selected model", async () => {
    const store = createChatStore(createWorkspaceDependencies());
    await store.getState().initialize("conversation-2");

    store.getState().newChat();

    expect(store.getState().conversationId).toBeNull();
    expect(store.getState().messages).toEqual([]);
    expect(store.getState().selectedProvider).toBe("provider-b");
    expect(store.getState().selectedModel).toBe("model-b");
  });

  it("refreshes conversation summaries after a successful stream", async () => {
    let listCalls = 0;
    const refreshed = [
      { ...conversations[0], title: "Hello", id: "conversation-1" },
    ];
    const store = createChatStore(
      createWorkspaceDependencies({
        fetchConversations: async () => {
          listCalls += 1;
          return listCalls === 1 ? conversations : refreshed;
        },
      }),
    );
    await store.getState().initialize(null);

    await store.getState().sendMessage("Hello");

    expect(listCalls).toBe(2);
    expect(store.getState().conversations).toEqual(refreshed);
  });

  it("ignores a stale conversation refresh response", async () => {
    const resolvers: Array<(items: ConversationSummary[]) => void> = [];
    let listCalls = 0;
    const store = createChatStore(
      createWorkspaceDependencies({
        fetchConversations: async () => {
          listCalls += 1;
          if (listCalls === 1) {
            return conversations;
          }
          return new Promise((resolve) => resolvers.push(resolve));
        },
      }),
    );
    await store.getState().initialize(null);

    const olderRefresh = store.getState().refreshConversations();
    const newerRefresh = store.getState().refreshConversations();
    const newest = [{ ...conversations[0], title: "Newest summary" }];
    const stale = [{ ...conversations[0], title: "Stale summary" }];
    resolvers[1]?.(newest);
    await newerRefresh;
    resolvers[0]?.(stale);
    await olderRefresh;

    expect(store.getState().conversations).toEqual(newest);
  });
});
