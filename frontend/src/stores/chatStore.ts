import { create } from "zustand";

import { streamChat } from "../api/chat";
import type {
  ChatCompletionRequest,
  ChatCompletionResponse,
  UiChatMessage,
} from "../types/chat";

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

type ChatStatus = "idle" | "streaming" | "error";

export type ChatStore = {
  messages: UiChatMessage[];
  conversationId: string | null;
  status: ChatStatus;
  error: string | null;
  activeRequestId: string | null;
  controller: AbortController | null;
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

export function createChatStore(streamer: StreamChatFunction = streamChat) {
  return create<ChatStore>((set, get) => ({
    messages: [],
    conversationId: null,
    status: "idle",
    error: null,
    activeRequestId: null,
    controller: null,

    async sendMessage(rawContent: string) {
      const content = rawContent.trim();
      if (!content || get().status === "streaming") {
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
        activeRequestId: requestId,
        controller,
      }));

      try {
        const response = await streamer(
          {
            conversation_id: get().conversationId,
            provider: DEFAULT_PROVIDER,
            model: DEFAULT_MODEL,
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
          error:
            aborted
              ? null
              : error instanceof Error
                ? error.message
                : "Streaming request failed",
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
      get().controller?.abort();
      set({
        messages: [],
        conversationId: null,
        status: "idle",
        error: null,
        activeRequestId: null,
        controller: null,
      });
    },
  }));
}

export const useChatStore = createChatStore();
