// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createRagStore,
  type RagStoreDependencies,
} from "../stores/ragStore";
import type { ConversationSummary } from "../types/conversations";
import type { KnowledgeBase } from "../types/knowledge";
import type { ModelOption } from "../types/models";
import type { RagChatResponse } from "../types/rag";
import RagChatPage, { selectRagOwnerView } from "./RagChatPage";

const knowledgeBase: KnowledgeBase = {
  id: "00000000-0000-0000-0000-000000000601",
  name: "Engineering notes",
  description: "Architecture and runbooks",
  embedding_provider: null,
  embedding_model: null,
  vector_store: "qdrant",
  vector_collection_name: null,
  created_at: "2026-08-02T14:00:00",
  updated_at: "2026-08-02T14:00:00",
};

const model: ModelOption = {
  provider: "mock",
  model: "mock-model",
  display_name: "Mock model",
  supports_streaming: false,
  supports_tools: false,
  supports_json: false,
  input_price_per_1m: null,
  output_price_per_1m: null,
};

const conversation: ConversationSummary = {
  id: "00000000-0000-0000-0000-000000000602",
  title: "RAG · Engineering notes",
  default_provider: "mock",
  default_model: "mock-model",
  created_at: "2026-08-02T14:00:01",
  updated_at: "2026-08-02T14:00:01",
};

const response: RagChatResponse = {
  conversation_id: conversation.id,
  rag_query_id: "00000000-0000-0000-0000-000000000603",
  user_message: {
    id: "00000000-0000-0000-0000-000000000604",
    conversation_id: conversation.id,
    role: "user",
    content: "What changed?",
    model: null,
    provider: null,
    created_at: "2026-08-02T14:00:02",
  },
  assistant_message: {
    id: "00000000-0000-0000-0000-000000000605",
    conversation_id: conversation.id,
    role: "assistant",
    content: "Routes remain thin [1].",
    model: "mock-model",
    provider: "mock",
    created_at: "2026-08-02T14:00:03",
  },
  answer: "Routes remain thin [1].",
  sources: [
    {
      source_index: 1,
      knowledge_base_id: knowledgeBase.id,
      document_id: "00000000-0000-0000-0000-000000000606",
      chunk_id: "00000000-0000-0000-0000-000000000607",
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
    knowledge_base_id: knowledgeBase.id,
    top_k: 5,
    score_threshold: null,
    result_count: 1,
    used_source_count: 1,
    context_characters: 96,
  },
  provider: "mock",
  model: "mock-model",
  usage: null,
  llm_call_id: "00000000-0000-0000-0000-000000000608",
};

const reactTestEnvironment = globalThis as typeof globalThis & {
  IS_REACT_ACT_ENVIRONMENT: boolean;
};

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function dependencies(
  overrides: Partial<RagStoreDependencies> = {},
): RagStoreDependencies {
  return {
    createConversation: async () => conversation,
    createRagChat: async () => response,
    fetchModels: async () => [model],
    defaultProvider: "mock",
    defaultModel: "mock-model",
    ...overrides,
  };
}

async function flushEffects(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function mountPage(
  store = createRagStore(dependencies()),
): { container: HTMLDivElement; root: Root } {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  act(() => {
    root.render(<RagChatPage knowledgeBase={knowledgeBase} ragStore={store} />);
  });
  return { container, root };
}

function setTextarea(textarea: HTMLTextAreaElement, value: string): void {
  const setter = Object.getOwnPropertyDescriptor(
    HTMLTextAreaElement.prototype,
    "value",
  )?.set;
  setter?.call(textarea, value);
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

function composer(container: HTMLElement): {
  form: HTMLFormElement;
  textarea: HTMLTextAreaElement;
} {
  const form = container.querySelector('form[aria-label="Ask Knowledge Base"]');
  const textarea = form?.querySelector("textarea");
  if (!(form instanceof HTMLFormElement) || !(textarea instanceof HTMLTextAreaElement)) {
    throw new Error("RAG composer is missing");
  }
  return { form, textarea };
}

beforeEach(() => {
  reactTestEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
});

afterEach(() => {
  document.body.replaceChildren();
  vi.clearAllMocks();
});

describe("RagChatPage", () => {
  it("hides turns until the store owner matches the visible Knowledge Base", () => {
    const oldTurn = { query: "What changed?", ...response };

    expect(
      selectRagOwnerView(
        knowledgeBase.id,
        "00000000-0000-0000-0000-000000000699",
        [oldTurn],
      ),
    ).toEqual({ ownerCurrent: false, turns: [] });
    expect(
      selectRagOwnerView(knowledgeBase.id, knowledgeBase.id, [oldTurn]),
    ).toEqual({ ownerCurrent: true, turns: [oldTurn] });
  });

  it("shows model loading before the selected Knowledge Base becomes ready", async () => {
    const pendingModels = deferred<ModelOption[]>();
    const store = createRagStore(
      dependencies({ fetchModels: () => pendingModels.promise }),
    );
    const { container, root } = mountPage(store);

    expect(container.textContent).toContain("Loading RAG models...");
    expect(container.textContent).toContain("Ask Engineering notes");

    await act(async () => {
      pendingModels.resolve([model]);
      await pendingModels.promise;
    });
    await flushEffects();
    expect(container.textContent).toContain("Mock model");
    act(() => root.unmount());
  });

  it("retries a safe model initialization failure", async () => {
    let calls = 0;
    const store = createRagStore(
      dependencies({
        fetchModels: async () => {
          calls += 1;
          if (calls === 1) {
            throw new Error("Model Registry unavailable");
          }
          return [model];
        },
      }),
    );
    const { container, root } = mountPage(store);
    await flushEffects();
    expect(container.textContent).toContain("Model Registry unavailable");

    const retry = [...container.querySelectorAll("button")].find(
      (button) => button.textContent?.trim() === "Retry",
    );
    await act(async () => {
      retry?.click();
      await Promise.resolve();
    });
    await flushEffects();

    expect(calls).toBe(2);
    expect(container.textContent).toContain("Mock model");
    act(() => root.unmount());
  });

  it("shows an explicit state and disables questions when no model exists", async () => {
    const store = createRagStore(
      dependencies({ fetchModels: async () => [] }),
    );
    const { container, root } = mountPage(store);
    await flushEffects();

    expect(container.textContent).toContain("No models configured for RAG Chat");
    const { textarea } = composer(container);
    expect(textarea.disabled).toBe(true);
    act(() => root.unmount());
  });

  it("asks a non-streaming question and displays the answer", async () => {
    const createConversation = vi.fn(async () => conversation);
    const createRagChat = vi.fn(async () => response);
    const store = createRagStore(
      dependencies({ createConversation, createRagChat }),
    );
    const { container, root } = mountPage(store);
    await flushEffects();
    const { form, textarea } = composer(container);

    act(() => setTextarea(textarea, "  What changed?  "));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });
    await flushEffects();

    expect(createConversation).toHaveBeenCalledTimes(1);
    expect(createRagChat).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain("What changed?");
    expect(container.textContent).toContain("Routes remain thin [1].");
    expect(textarea.value).toBe("");
    act(() => root.unmount());
  });

  it("preserves the question after a safe request failure", async () => {
    const store = createRagStore(
      dependencies({
        createRagChat: async () => {
          throw new Error("Vector store unavailable");
        },
      }),
    );
    const { container, root } = mountPage(store);
    await flushEffects();
    const { form, textarea } = composer(container);

    act(() => setTextarea(textarea, "What changed?"));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });
    await flushEffects();

    expect(container.textContent).toContain("Vector store unavailable");
    expect(textarea.value).toBe("What changed?");
    act(() => root.unmount());
  });

  it("disables conflicting RAG controls while a request is pending", async () => {
    const pending = deferred<RagChatResponse>();
    const store = createRagStore(
      dependencies({ createRagChat: () => pending.promise }),
    );
    const { container, root } = mountPage(store);
    await flushEffects();
    const { form, textarea } = composer(container);

    act(() => setTextarea(textarea, "What changed?"));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });

    const modelSelect = container.querySelector('select[aria-label="Model"]');
    const newChat = [...container.querySelectorAll("button")].find(
      (button) => button.textContent?.trim() === "New RAG chat",
    );
    expect(container.textContent).toContain("Asking...");
    expect(textarea.disabled).toBe(true);
    expect((modelSelect as HTMLSelectElement).disabled).toBe(true);
    expect((newChat as HTMLButtonElement).disabled).toBe(true);

    await act(async () => {
      pending.resolve(response);
      await pending.promise;
    });
    await flushEffects();
    act(() => root.unmount());
  });

  it("starts a new RAG chat and clears the current-session answer", async () => {
    const store = createRagStore(dependencies());
    const { container, root } = mountPage(store);
    await flushEffects();
    const { form, textarea } = composer(container);
    act(() => setTextarea(textarea, "What changed?"));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });
    await flushEffects();
    expect(container.textContent).toContain("Routes remain thin [1].");

    const newChat = [...container.querySelectorAll("button")].find(
      (button) => button.textContent?.trim() === "New RAG chat",
    );
    act(() => newChat?.click());

    expect(container.textContent).not.toContain("Routes remain thin [1].");
    expect(container.textContent).toContain("Ask a question to start a grounded conversation");
    act(() => root.unmount());
  });
});
