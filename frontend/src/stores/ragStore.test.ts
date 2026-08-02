import { describe, expect, it, vi } from "vitest";

import {
  createRagStore,
  type RagStoreDependencies,
} from "./ragStore";
import type { ConversationSummary } from "../types/conversations";
import type { ModelOption } from "../types/models";
import type {
  RagChatRequest,
  RagChatResponse,
} from "../types/rag";

const knowledgeBaseId = "00000000-0000-0000-0000-000000000501";
const otherKnowledgeBaseId = "00000000-0000-0000-0000-000000000502";
const conversationId = "00000000-0000-0000-0000-000000000503";

const models: ModelOption[] = [
  {
    provider: "provider-a",
    model: "model-a",
    display_name: "Model A",
    supports_streaming: false,
    supports_tools: false,
    supports_json: false,
    input_price_per_1m: null,
    output_price_per_1m: null,
  },
  {
    provider: "mock",
    model: "mock-model",
    display_name: "Mock model",
    supports_streaming: false,
    supports_tools: false,
    supports_json: false,
    input_price_per_1m: null,
    output_price_per_1m: null,
  },
];

const conversation: ConversationSummary = {
  id: conversationId,
  title: "RAG · Engineering notes",
  default_provider: "mock",
  default_model: "mock-model",
  created_at: "2026-08-02T13:00:00",
  updated_at: "2026-08-02T13:00:00",
};

function createResponse(
  overrides: Partial<RagChatResponse> = {},
): RagChatResponse {
  return {
    conversation_id: conversationId,
    rag_query_id: "00000000-0000-0000-0000-000000000504",
    user_message: {
      id: "00000000-0000-0000-0000-000000000505",
      conversation_id: conversationId,
      role: "user",
      content: "What changed?",
      model: null,
      provider: null,
      created_at: "2026-08-02T13:00:01",
    },
    assistant_message: {
      id: "00000000-0000-0000-0000-000000000506",
      conversation_id: conversationId,
      role: "assistant",
      content: "Routes remain thin [1].",
      model: "mock-model",
      provider: "mock",
      created_at: "2026-08-02T13:00:02",
    },
    answer: "Routes remain thin [1].",
    sources: [
      {
        source_index: 1,
        knowledge_base_id: knowledgeBaseId,
        document_id: "00000000-0000-0000-0000-000000000507",
        chunk_id: "00000000-0000-0000-0000-000000000508",
        embedding_provider: "openai_compatible",
        embedding_model: "text-embedding-3-small",
        filename: "architecture.md",
        chunk_index: 3,
        content: "Routes remain thin and delegate to services.",
        score: 0.91,
        heading: "API boundary",
        page_number: null,
        metadata: { source_format: "md" },
      },
    ],
    metadata: {
      strategy: "naive_vector",
      knowledge_base_id: knowledgeBaseId,
      top_k: 5,
      score_threshold: null,
      result_count: 1,
      used_source_count: 1,
      context_characters: 96,
    },
    provider: "mock",
    model: "mock-model",
    usage: {
      input_tokens: 60,
      output_tokens: 8,
      total_tokens: 68,
    },
    llm_call_id: "00000000-0000-0000-0000-000000000509",
    ...overrides,
  };
}

function createDependencies(
  overrides: Partial<RagStoreDependencies> = {},
): RagStoreDependencies {
  return {
    createConversation: async () => conversation,
    createRagChat: async () => createResponse(),
    fetchModels: async () => models,
    defaultProvider: "mock",
    defaultModel: "mock-model",
    ...overrides,
  };
}

describe("RAG store", () => {
  it("initializes the configured model and completes a first dedicated turn", async () => {
    const createConversation = vi.fn(async () => conversation);
    const createRagChat = vi.fn(async () => createResponse());
    const store = createRagStore(
      createDependencies({ createConversation, createRagChat }),
    );

    await store.getState().initialize();
    store.getState().setKnowledgeBase(knowledgeBaseId, "Engineering notes");
    await expect(store.getState().sendQuery("  What changed?  ")).resolves.toBe(
      true,
    );

    expect(createConversation).toHaveBeenCalledWith({
      title: "RAG · Engineering notes",
      default_provider: "mock",
      default_model: "mock-model",
    });
    const [request, options] = createRagChat.mock.calls[0] as unknown as [
      RagChatRequest,
      { signal: AbortSignal },
    ];
    expect(request).toEqual({
      conversation_id: conversationId,
      knowledge_base_id: knowledgeBaseId,
      provider: "mock",
      model: "mock-model",
      query: "What changed?",
      top_k: 5,
      temperature: 0.2,
    });
    expect(options.signal).toBeInstanceOf(AbortSignal);
    expect(store.getState()).toMatchObject({
      conversationId,
      requestStatus: "idle",
      requestError: null,
    });
    expect(store.getState().turns).toEqual([
      {
        query: "What changed?",
        ...createResponse(),
      },
    ]);
  });

  it("bounds the dedicated Conversation title by Unicode code points", async () => {
    const createConversation = vi.fn(async () => conversation);
    const store = createRagStore(createDependencies({ createConversation }));
    const longKnowledgeBaseName = "😀".repeat(255);
    const expectedTitle = [...`RAG · ${longKnowledgeBaseName}`]
      .slice(0, 255)
      .join("");

    await store.getState().initialize();
    store.getState().setKnowledgeBase(knowledgeBaseId, longKnowledgeBaseName);
    await store.getState().sendQuery("What changed?");

    expect(createConversation).toHaveBeenCalledWith(
      expect.objectContaining({ title: expectedTitle }),
    );
    expect([...expectedTitle]).toHaveLength(255);
  });

  it("falls back to the first model and exposes an explicit no-model state", async () => {
    const fallbackStore = createRagStore(
      createDependencies({
        defaultProvider: "missing",
        defaultModel: "missing",
      }),
    );
    await fallbackStore.getState().initialize();
    expect(fallbackStore.getState()).toMatchObject({
      selectedProvider: "provider-a",
      selectedModel: "model-a",
      workspaceStatus: "ready",
    });

    const emptyStore = createRagStore(
      createDependencies({ fetchModels: async () => [] }),
    );
    await emptyStore.getState().initialize();
    expect(emptyStore.getState()).toMatchObject({
      models: [],
      selectedProvider: null,
      selectedModel: null,
      workspaceStatus: "ready",
    });
  });

  it("reuses the dedicated Conversation for later turns", async () => {
    const createConversation = vi.fn(async () => conversation);
    let responseNumber = 0;
    const createRagChat = vi.fn(async (request: RagChatRequest) => {
      responseNumber += 1;
      return createResponse({
        user_message: {
          ...createResponse().user_message,
          id: `user-${responseNumber}`,
          content: request.query,
        },
        assistant_message: {
          ...createResponse().assistant_message,
          id: `assistant-${responseNumber}`,
        },
        rag_query_id: `rag-${responseNumber}`,
      });
    });
    const store = createRagStore(
      createDependencies({ createConversation, createRagChat }),
    );
    await store.getState().initialize();
    store.getState().setKnowledgeBase(knowledgeBaseId, "Engineering notes");

    await store.getState().sendQuery("First question");
    await store.getState().sendQuery("Second question");

    expect(createConversation).toHaveBeenCalledTimes(1);
    expect(createRagChat).toHaveBeenCalledTimes(2);
    expect(createRagChat.mock.calls[1]?.[0].conversation_id).toBe(
      conversationId,
    );
    expect(store.getState().turns).toHaveLength(2);
  });

  it("preserves session selection while exposing a safe request failure", async () => {
    const store = createRagStore(
      createDependencies({
        createRagChat: async () => {
          throw new Error("Vector store unavailable");
        },
      }),
    );
    await store.getState().initialize();
    store.getState().setKnowledgeBase(knowledgeBaseId, "Engineering notes");

    await expect(store.getState().sendQuery("What changed?")).resolves.toBe(
      false,
    );

    expect(store.getState()).toMatchObject({
      selectedKnowledgeBaseId: knowledgeBaseId,
      conversationId,
      turns: [],
      requestStatus: "error",
      requestError: "Vector store unavailable",
    });
  });

  it("starts a new RAG chat without clearing owner or model selection", async () => {
    const store = createRagStore(createDependencies());
    await store.getState().initialize();
    store.getState().setKnowledgeBase(knowledgeBaseId, "Engineering notes");
    await store.getState().sendQuery("What changed?");

    store.getState().newChat();

    expect(store.getState()).toMatchObject({
      selectedKnowledgeBaseId: knowledgeBaseId,
      selectedProvider: "mock",
      selectedModel: "mock-model",
      conversationId: null,
      turns: [],
      requestStatus: "idle",
      requestError: null,
    });
  });

  it("ignores a late response after the Knowledge Base owner changes", async () => {
    let resolveChat: ((response: RagChatResponse) => void) | undefined;
    let receivedSignal: AbortSignal | undefined;
    const store = createRagStore(
      createDependencies({
        createRagChat: (_request, options) => {
          receivedSignal = options?.signal;
          return new Promise((resolve) => {
            resolveChat = resolve;
          });
        },
      }),
    );
    await store.getState().initialize();
    store.getState().setKnowledgeBase(knowledgeBaseId, "Engineering notes");
    const pending = store.getState().sendQuery("What changed?");
    await Promise.resolve();
    await Promise.resolve();

    store.getState().setKnowledgeBase(otherKnowledgeBaseId, "Other notes");
    expect(receivedSignal?.aborted).toBe(true);
    resolveChat?.(createResponse());
    await expect(pending).resolves.toBe(false);
    expect(store.getState()).toMatchObject({
      selectedKnowledgeBaseId: otherKnowledgeBaseId,
      conversationId: null,
      turns: [],
      requestStatus: "idle",
    });
  });

  it.each([
    {
      name: "response Knowledge Base",
      response: () =>
        createResponse({
          metadata: {
            ...createResponse().metadata,
            knowledge_base_id: otherKnowledgeBaseId,
          },
        }),
      message: "RAG API returned inconsistent response ownership",
    },
    {
      name: "source Knowledge Base",
      response: () =>
        createResponse({
          sources: [
            {
              ...createResponse().sources[0],
              knowledge_base_id: otherKnowledgeBaseId,
            },
          ],
        }),
      message: "RAG API returned inconsistent source metadata",
    },
    {
      name: "source index",
      response: () =>
        createResponse({
          sources: [{ ...createResponse().sources[0], source_index: 2 }],
        }),
      message: "RAG API returned inconsistent source metadata",
    },
    {
      name: "used source count",
      response: () =>
        createResponse({
          metadata: {
            ...createResponse().metadata,
            used_source_count: 0,
          },
        }),
      message: "RAG API returned inconsistent source metadata",
    },
  ])("rejects inconsistent $name", async ({ response, message }) => {
    const store = createRagStore(
      createDependencies({ createRagChat: async () => response() }),
    );
    await store.getState().initialize();
    store.getState().setKnowledgeBase(knowledgeBaseId, "Engineering notes");

    await expect(store.getState().sendQuery("What changed?")).resolves.toBe(
      false,
    );
    expect(store.getState()).toMatchObject({
      turns: [],
      requestStatus: "error",
      requestError: message,
    });
  });

  it("rejects a response for another Conversation", async () => {
    const store = createRagStore(
      createDependencies({
        createRagChat: async () =>
          createResponse({
            conversation_id: "00000000-0000-0000-0000-000000000599",
          }),
      }),
    );
    await store.getState().initialize();
    store.getState().setKnowledgeBase(knowledgeBaseId, "Engineering notes");

    await expect(store.getState().sendQuery("What changed?")).resolves.toBe(
      false,
    );
    expect(store.getState().requestError).toBe(
      "RAG API returned inconsistent response ownership",
    );
  });
});
