// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { RagTurn } from "../../types/rag";
import RagAnswerPanel from "./RagAnswerPanel";

const turn: RagTurn = {
  query: "What changed?",
  conversation_id: "00000000-0000-0000-0000-000000000801",
  rag_query_id: "00000000-0000-0000-0000-000000000802",
  user_message: {
    id: "00000000-0000-0000-0000-000000000803",
    conversation_id: "00000000-0000-0000-0000-000000000801",
    role: "user",
    content: "What changed?",
    model: null,
    provider: null,
    created_at: "2026-08-02T15:00:00",
  },
  assistant_message: {
    id: "00000000-0000-0000-0000-000000000804",
    conversation_id: "00000000-0000-0000-0000-000000000801",
    role: "assistant",
    content: "Routes remain thin [1].",
    model: "mock-model",
    provider: "mock",
    created_at: "2026-08-02T15:00:01",
  },
  answer: "Routes remain thin [1].",
  sources: [
    {
      source_index: 1,
      knowledge_base_id: "00000000-0000-0000-0000-000000000805",
      document_id: "00000000-0000-0000-0000-000000000806",
      chunk_id: "00000000-0000-0000-0000-000000000807",
      embedding_provider: "openai_compatible",
      embedding_model: "text-embedding-3-small",
      filename: "architecture.md",
      chunk_index: 2,
      content: "Routes delegate business work to services.",
      score: 0.9321,
      heading: "Runtime boundaries",
      page_number: null,
      metadata: { source_format: "md" },
    },
  ],
  metadata: {
    strategy: "naive_vector",
    knowledge_base_id: "00000000-0000-0000-0000-000000000805",
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
  llm_call_id: "00000000-0000-0000-0000-000000000808",
};

const reactTestEnvironment = globalThis as typeof globalThis & {
  IS_REACT_ACT_ENVIRONMENT: boolean;
};

function mountPanel(value: RagTurn): {
  container: HTMLDivElement;
  root: Root;
} {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  act(() => {
    root.render(<RagAnswerPanel turn={value} />);
  });
  return { container, root };
}

beforeEach(() => {
  reactTestEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
});

afterEach(() => {
  document.body.replaceChildren();
});

describe("RagAnswerPanel", () => {
  it("renders the answer, audit IDs, retrieval metadata, usage, and sources", () => {
    const { container, root } = mountPanel(turn);
    const text = container.textContent ?? "";

    expect(text).toContain("What changed?");
    expect(text).toContain("Routes remain thin [1].");
    expect(text).toContain(turn.rag_query_id);
    expect(text).toContain(turn.llm_call_id);
    expect(text).toContain(turn.conversation_id);
    expect(text).toContain("naive_vector");
    expect(text).toContain("Top-K 5");
    expect(text).toContain("1 retrieved");
    expect(text).toContain("1 used");
    expect(text).toContain("96 context characters");
    expect(text).toContain("mock / mock-model");
    expect(text).toContain("68 tokens");
    expect(text).toContain("architecture.md");
    expect(text).toContain("Routes delegate business work to services.");
    act(() => root.unmount());
  });

  it("renders an untrusted answer only as text", () => {
    const untrusted = '<script>globalThis.compromised=true</script>';
    const { container, root } = mountPanel({
      ...turn,
      answer: untrusted,
      assistant_message: { ...turn.assistant_message, content: untrusted },
    });

    expect(container.textContent).toContain(untrusted);
    expect(container.querySelector("script")).toBeNull();
    expect((globalThis as { compromised?: boolean }).compromised).toBeUndefined();
    act(() => root.unmount());
  });
});
