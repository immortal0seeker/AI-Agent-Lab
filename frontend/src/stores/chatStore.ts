import { create } from "zustand";

import { streamChat } from "../api/chat";
import {
  fetchConversationMessages,
  fetchConversations,
} from "../api/conversations";
import { fetchModels } from "../api/models";
import type {
  ApiMessage,
  ChatCompletionRequest,
  ChatCompletionResponse,
  UiChatMessage,
} from "../types/chat";
import type { ConversationSummary } from "../types/conversations";
import type { ModelOption } from "../types/models";

export const DEFAULT_PROVIDER =
  import.meta.env.VITE_DEFAULT_PROVIDER ?? "openai_compatible";
export const DEFAULT_MODEL =
  import.meta.env.VITE_DEFAULT_MODEL ?? "example-model";

type StreamChatOptions = {
  signal?: AbortSignal;
  onDelta: (content: string) => void;
};

export type StreamChatFunction = (
  request: ChatCompletionRequest,
  options: StreamChatOptions,
) => Promise<ChatCompletionResponse>;

export type ChatStoreDependencies = {
  streamChat: StreamChatFunction;
  fetchModels: () => Promise<ModelOption[]>;
  fetchConversations: () => Promise<ConversationSummary[]>;
  fetchConversationMessages: (conversationId: string) => Promise<ApiMessage[]>;
  defaultProvider: string;
  defaultModel: string;
};

type ChatStatus = "idle" | "streaming" | "error";
type WorkspaceStatus = "idle" | "loading" | "ready" | "error";
type ConversationStatus = "idle" | "loading" | "error";

export type ChatStore = {
  messages: UiChatMessage[];
  models: ModelOption[];
  conversations: ConversationSummary[];
  conversationId: string | null;
  selectedProvider: string | null;
  selectedModel: string | null;
  status: ChatStatus;
  workspaceStatus: WorkspaceStatus;
  conversationStatus: ConversationStatus;
  error: string | null;
  workspaceError: string | null;
  activeRequestId: string | null;
  selectionRequestId: string | null;
  controller: AbortController | null;
  initialize: (conversationId: string | null) => Promise<void>;
  selectModel: (provider: string, model: string) => void;
  selectConversation: (conversationId: string) => Promise<void>;
  refreshConversations: () => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  stopGeneration: () => void;
  newChat: () => void;
};

let localId = 0;

function createLocalId(prefix: string): string {
  localId += 1;
  return `${prefix}-${localId}`;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function isSelectableModel(
  models: ModelOption[],
  provider: string | null,
  model: string | null,
): provider is string {
  return (
    provider !== null &&
    model !== null &&
    models.some(
      (option) => option.provider === provider && option.model === model,
    )
  );
}

function toUiMessages(messages: ApiMessage[]): UiChatMessage[] {
  return messages
    .filter(
      (message): message is ApiMessage & { role: "user" | "assistant" } =>
        message.role === "user" || message.role === "assistant",
    )
    .map((message) => ({
      id: message.id,
      role: message.role,
      content: message.content,
      status: "complete",
    }));
}

const productionDependencies: ChatStoreDependencies = {
  streamChat,
  fetchModels,
  fetchConversations,
  fetchConversationMessages,
  defaultProvider: DEFAULT_PROVIDER,
  defaultModel: DEFAULT_MODEL,
};

export function createChatStore(
  overrides: Partial<ChatStoreDependencies> = {},
) {
  const dependencies = { ...productionDependencies, ...overrides };
  let pendingInitialConversationId: string | null = null;

  return create<ChatStore>((set, get) => ({
    messages: [],
    models: [],
    conversations: [],
    conversationId: null,
    selectedProvider: dependencies.defaultProvider,
    selectedModel: dependencies.defaultModel,
    status: "idle",
    workspaceStatus: "idle",
    conversationStatus: "idle",
    error: null,
    workspaceError: null,
    activeRequestId: null,
    selectionRequestId: null,
    controller: null,

    async initialize(conversationId: string | null) {
      if (
        get().workspaceStatus === "loading" ||
        get().workspaceStatus === "ready"
      ) {
        return;
      }

      pendingInitialConversationId = conversationId;
      set({ workspaceStatus: "loading", workspaceError: null });
      try {
        const [models, conversations] = await Promise.all([
          dependencies.fetchModels(),
          dependencies.fetchConversations(),
        ]);
        const configuredModel = models.find(
          (option) =>
            option.provider === dependencies.defaultProvider &&
            option.model === dependencies.defaultModel,
        );
        const selected = configuredModel ?? models[0] ?? null;
        set({
          models,
          conversations,
          selectedProvider: selected?.provider ?? null,
          selectedModel: selected?.model ?? null,
        });

        if (
          conversationId !== null &&
          pendingInitialConversationId === conversationId &&
          conversations.some((conversation) => conversation.id === conversationId)
        ) {
          await get().selectConversation(conversationId);
        }
        set({ workspaceStatus: "ready" });
      } catch (error: unknown) {
        set({
          workspaceStatus: "error",
          workspaceError: errorMessage(
            error,
            "Unable to initialize Chat workspace",
          ),
        });
      }
    },

    selectModel(provider: string, model: string) {
      if (
        get().status === "streaming" ||
        !isSelectableModel(get().models, provider, model)
      ) {
        return;
      }
      set({
        selectedProvider: provider,
        selectedModel: model,
        workspaceError: null,
      });
    },

    async selectConversation(conversationId: string) {
      if (get().status === "streaming") {
        return;
      }
      const conversation = get().conversations.find(
        (item) => item.id === conversationId,
      );
      if (conversation === undefined) {
        set({ workspaceError: "Conversation is not available" });
        return;
      }

      const requestId = createLocalId("selection");
      set({
        conversationStatus: "loading",
        workspaceError: null,
        selectionRequestId: requestId,
      });
      try {
        const messages = await dependencies.fetchConversationMessages(
          conversationId,
        );
        if (get().selectionRequestId !== requestId) {
          return;
        }

        const nextState: Partial<ChatStore> = {
          conversationId,
          messages: toUiMessages(messages),
          conversationStatus: "idle",
          selectionRequestId: null,
          error: null,
        };
        if (
          isSelectableModel(
            get().models,
            conversation.default_provider,
            conversation.default_model,
          )
        ) {
          nextState.selectedProvider = conversation.default_provider;
          nextState.selectedModel = conversation.default_model;
        }
        set(nextState);
      } catch (error: unknown) {
        if (get().selectionRequestId !== requestId) {
          return;
        }
        set({
          conversationStatus: "error",
          workspaceError: errorMessage(
            error,
            "Unable to load conversation messages",
          ),
          selectionRequestId: null,
        });
      }
    },

    async refreshConversations() {
      try {
        const conversations = await dependencies.fetchConversations();
        set({ conversations, workspaceError: null });
      } catch (error: unknown) {
        set({
          workspaceError: errorMessage(
            error,
            "Unable to refresh conversations",
          ),
        });
      }
    },

    async sendMessage(rawContent: string) {
      const content = rawContent.trim();
      const provider = get().selectedProvider;
      const model = get().selectedModel;
      if (!content || get().status === "streaming") {
        return;
      }
      if (provider === null || model === null) {
        set({ workspaceError: "No model is available for Chat" });
        return;
      }

      const requestId = createLocalId("request");
      const userId = createLocalId("user");
      const assistantId = createLocalId("assistant");
      const controller = new AbortController();
      const userMessage: UiChatMessage = {
        id: userId,
        role: "user",
        content,
        status: "complete",
      };
      const assistantMessage: UiChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        status: "streaming",
      };

      set((state) => ({
        messages: [...state.messages, userMessage, assistantMessage],
        status: "streaming",
        error: null,
        workspaceError: null,
        activeRequestId: requestId,
        controller,
      }));

      try {
        const response = await dependencies.streamChat(
          {
            conversation_id: get().conversationId,
            provider,
            model,
            content,
          },
          {
            signal: controller.signal,
            onDelta(delta) {
              if (get().activeRequestId !== requestId) {
                return;
              }
              set((state) => ({
                messages: state.messages.map((message) =>
                  message.id === assistantId
                    ? { ...message, content: message.content + delta }
                    : message,
                ),
              }));
            },
          },
        );

        if (get().activeRequestId !== requestId) {
          return;
        }
        set((state) => ({
          conversationId: response.conversation_id,
          messages: state.messages.map((message) => {
            if (message.id === userId) {
              return {
                id: response.user_message.id,
                role: "user",
                content: response.user_message.content,
                status: "complete",
              };
            }
            if (message.id === assistantId) {
              return {
                id: response.assistant_message.id,
                role: "assistant",
                content: response.assistant_message.content,
                status: "complete",
              };
            }
            return message;
          }),
          status: "idle",
          error: null,
        }));
        await get().refreshConversations();
      } catch (error: unknown) {
        if (get().activeRequestId !== requestId) {
          return;
        }
        const aborted = isAbortError(error);
        set((state) => ({
          messages: state.messages.map((message) =>
            message.id === assistantId
              ? { ...message, status: aborted ? "stopped" : "error" }
              : message,
          ),
          status: aborted ? "idle" : "error",
          error: aborted
            ? null
            : errorMessage(error, "Streaming request failed"),
        }));
      } finally {
        if (get().activeRequestId === requestId) {
          set({ activeRequestId: null, controller: null });
        }
      }
    },

    stopGeneration() {
      const controller = get().controller;
      if (controller === null) {
        return;
      }
      set((state) => ({
        messages: state.messages.map((message) =>
          message.status === "streaming"
            ? { ...message, status: "stopped" }
            : message,
        ),
        status: "idle",
        error: null,
        activeRequestId: null,
        controller: null,
      }));
      controller.abort();
    },

    newChat() {
      pendingInitialConversationId = null;
      get().controller?.abort();
      set({
        messages: [],
        conversationId: null,
        status: "idle",
        conversationStatus: "idle",
        error: null,
        workspaceError: null,
        activeRequestId: null,
        selectionRequestId: null,
        controller: null,
      });
    },
  }));
}

export const useChatStore = createChatStore();
