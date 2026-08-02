import { create } from "zustand";

import { createConversation } from "../api/conversations";
import { fetchModels } from "../api/models";
import { createRagChat } from "../api/rag";
import type { ConversationCreate, ConversationSummary } from "../types/conversations";
import type { ModelOption } from "../types/models";
import type {
  RagChatRequest,
  RagChatResponse,
  RagTurn,
} from "../types/rag";

const DEFAULT_PROVIDER =
  import.meta.env.VITE_DEFAULT_PROVIDER ?? "openai_compatible";
const DEFAULT_MODEL = import.meta.env.VITE_DEFAULT_MODEL ?? "example-model";

type RagRequestOptions = {
  signal?: AbortSignal;
};

export type RagStoreDependencies = {
  createConversation: (
    request: ConversationCreate,
  ) => Promise<ConversationSummary>;
  createRagChat: (
    request: RagChatRequest,
    options?: RagRequestOptions,
  ) => Promise<RagChatResponse>;
  fetchModels: () => Promise<ModelOption[]>;
  defaultProvider: string;
  defaultModel: string;
};

type RagWorkspaceStatus = "idle" | "loading" | "ready" | "error";
type RagRequestStatus = "idle" | "sending" | "error";

export type RagStore = {
  models: ModelOption[];
  selectedKnowledgeBaseId: string | null;
  selectedKnowledgeBaseName: string | null;
  selectedProvider: string | null;
  selectedModel: string | null;
  conversationId: string | null;
  turns: RagTurn[];
  workspaceStatus: RagWorkspaceStatus;
  requestStatus: RagRequestStatus;
  workspaceError: string | null;
  requestError: string | null;
  initialize: () => Promise<void>;
  setKnowledgeBase: (id: string, name: string) => void;
  selectModel: (provider: string, model: string) => void;
  sendQuery: (query: string) => Promise<boolean>;
  newChat: () => void;
};

const productionDependencies: RagStoreDependencies = {
  createConversation,
  createRagChat,
  fetchModels,
  defaultProvider: DEFAULT_PROVIDER,
  defaultModel: DEFAULT_MODEL,
};

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function truncateCodePoints(value: string, maxLength: number): string {
  return [...value].slice(0, maxLength).join("");
}

function validateResponse(
  response: RagChatResponse,
  conversationId: string,
  knowledgeBaseId: string,
): void {
  if (
    response.conversation_id !== conversationId ||
    response.metadata.knowledge_base_id !== knowledgeBaseId
  ) {
    throw new Error("RAG API returned inconsistent response ownership");
  }
  if (
    response.metadata.used_source_count !== response.sources.length ||
    response.sources.some(
      (source, index) =>
        source.knowledge_base_id !== knowledgeBaseId ||
        source.source_index !== index + 1,
    )
  ) {
    throw new Error("RAG API returned inconsistent source metadata");
  }
}

export function createRagStore(
  overrides: Partial<RagStoreDependencies> = {},
) {
  const dependencies = { ...productionDependencies, ...overrides };
  let requestSequence = 0;
  let initializationSequence = 0;
  let activeController: AbortController | null = null;

  return create<RagStore>((set, get) => {
    const invalidateRequest = () => {
      requestSequence += 1;
      activeController?.abort();
      activeController = null;
    };

    const ownsRequest = (request: number, knowledgeBaseId: string) =>
      request === requestSequence &&
      get().selectedKnowledgeBaseId === knowledgeBaseId;

    return {
      models: [],
      selectedKnowledgeBaseId: null,
      selectedKnowledgeBaseName: null,
      selectedProvider: dependencies.defaultProvider,
      selectedModel: dependencies.defaultModel,
      conversationId: null,
      turns: [],
      workspaceStatus: "idle",
      requestStatus: "idle",
      workspaceError: null,
      requestError: null,

      async initialize() {
        if (
          get().workspaceStatus === "loading" ||
          get().workspaceStatus === "ready"
        ) {
          return;
        }
        const request = ++initializationSequence;
        set({ workspaceStatus: "loading", workspaceError: null });
        try {
          const models = await dependencies.fetchModels();
          if (request !== initializationSequence) {
            return;
          }
          const configured = models.find(
            (option) =>
              option.provider === dependencies.defaultProvider &&
              option.model === dependencies.defaultModel,
          );
          const selected = configured ?? models[0] ?? null;
          set({
            models,
            selectedProvider: selected?.provider ?? null,
            selectedModel: selected?.model ?? null,
            workspaceStatus: "ready",
            workspaceError: null,
          });
        } catch (error: unknown) {
          if (request !== initializationSequence) {
            return;
          }
          set({
            workspaceStatus: "error",
            workspaceError: errorMessage(
              error,
              "Unable to initialize RAG workspace",
            ),
          });
        }
      },

      setKnowledgeBase(id, name) {
        if (
          get().selectedKnowledgeBaseId === id &&
          get().selectedKnowledgeBaseName === name
        ) {
          return;
        }
        invalidateRequest();
        set({
          selectedKnowledgeBaseId: id,
          selectedKnowledgeBaseName: name,
          conversationId: null,
          turns: [],
          requestStatus: "idle",
          requestError: null,
        });
      },

      selectModel(provider, model) {
        if (get().requestStatus === "sending") {
          return;
        }
        set({
          selectedProvider: provider,
          selectedModel: model,
          requestError: null,
        });
      },

      async sendQuery(query) {
        const trimmedQuery = query.trim();
        const state = get();
        const knowledgeBaseId = state.selectedKnowledgeBaseId;
        const knowledgeBaseName = state.selectedKnowledgeBaseName;
        const provider = state.selectedProvider;
        const model = state.selectedModel;
        if (
          !trimmedQuery ||
          knowledgeBaseId === null ||
          knowledgeBaseName === null ||
          provider === null ||
          model === null ||
          state.workspaceStatus !== "ready" ||
          state.requestStatus === "sending"
        ) {
          return false;
        }

        const request = ++requestSequence;
        const controller = new AbortController();
        activeController = controller;
        set({ requestStatus: "sending", requestError: null });

        try {
          let currentConversationId = get().conversationId;
          if (currentConversationId === null) {
            const created = await dependencies.createConversation({
              title: truncateCodePoints(`RAG · ${knowledgeBaseName}`, 255),
              default_provider: provider,
              default_model: model,
            });
            if (!ownsRequest(request, knowledgeBaseId)) {
              return false;
            }
            currentConversationId = created.id;
            set({ conversationId: currentConversationId });
          }

          const response = await dependencies.createRagChat(
            {
              conversation_id: currentConversationId,
              knowledge_base_id: knowledgeBaseId,
              provider,
              model,
              query: trimmedQuery,
              top_k: 5,
              temperature: 0.2,
            },
            { signal: controller.signal },
          );
          if (!ownsRequest(request, knowledgeBaseId)) {
            return false;
          }
          validateResponse(response, currentConversationId, knowledgeBaseId);
          set((current) => ({
            turns: [
              ...current.turns,
              { query: trimmedQuery, ...response },
            ],
            requestStatus: "idle",
            requestError: null,
          }));
          return true;
        } catch (error: unknown) {
          if (!ownsRequest(request, knowledgeBaseId)) {
            return false;
          }
          set({
            requestStatus: "error",
            requestError: errorMessage(error, "RAG request failed"),
          });
          return false;
        } finally {
          if (ownsRequest(request, knowledgeBaseId)) {
            activeController = null;
          }
        }
      },

      newChat() {
        invalidateRequest();
        set({
          conversationId: null,
          turns: [],
          requestStatus: "idle",
          requestError: null,
        });
      },
    };
  });
}

export type RagStoreHook = ReturnType<typeof createRagStore>;

export const useRagStore = createRagStore();
