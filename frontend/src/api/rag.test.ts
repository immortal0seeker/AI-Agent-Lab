import { afterEach, describe, expect, it, vi } from "vitest";

import { createRagChat, queryKnowledgeBase } from "./rag";
import type {
  RagChatRequest,
  RagChatResponse,
  RagQueryResponse,
  RagRetrievalRequest,
} from "../types/rag";

const knowledgeBaseId = "00000000-0000-0000-0000-000000000401";
const conversationId = "00000000-0000-0000-0000-000000000402";
const ragQueryId = "00000000-0000-0000-0000-000000000403";

const queryRequest: RagRetrievalRequest = {
  knowledge_base_id: knowledgeBaseId,
  query: "What changed in the architecture?",
  top_k: 5,
  score_threshold: 0.5,
};

const retrievalResult = {
  knowledge_base_id: knowledgeBaseId,
  document_id: "00000000-0000-0000-0000-000000000404",
  chunk_id: "00000000-0000-0000-0000-000000000405",
  filename: "architecture.md",
  chunk_index: 2,
  content: "The workspace uses a thin API and service boundary.",
  score: 0.9321,
  heading: "Runtime boundaries",
  page_number: null,
  metadata: {
    source_format: "md",
    line_start: 18,
    nested: { reviewed: true },
  },
};

const source = {
  ...retrievalResult,
  source_index: 1,
};

const queryResponse: RagQueryResponse = {
  rag_query_id: ragQueryId,
  results: [retrievalResult],
  metadata: {
    strategy: "naive_vector",
    knowledge_base_id: knowledgeBaseId,
    top_k: 5,
    score_threshold: 0.5,
    result_count: 1,
  },
};

const chatRequest: RagChatRequest = {
  ...queryRequest,
  conversation_id: conversationId,
  provider: "mock",
  model: "mock-model",
  temperature: 0.2,
  max_tokens: 512,
};

const chatResponse: RagChatResponse = {
  conversation_id: conversationId,
  rag_query_id: ragQueryId,
  user_message: {
    id: "00000000-0000-0000-0000-000000000406",
    conversation_id: conversationId,
    role: "user",
    content: chatRequest.query,
    model: null,
    provider: null,
    created_at: "2026-08-02T12:00:00",
  },
  assistant_message: {
    id: "00000000-0000-0000-0000-000000000407",
    conversation_id: conversationId,
    role: "assistant",
    content: "The workspace keeps routes thin [1].",
    model: "mock-model",
    provider: "mock",
    created_at: "2026-08-02T12:00:01",
  },
  answer: "The workspace keeps routes thin [1].",
  sources: [source],
  metadata: {
    strategy: "naive_vector",
    knowledge_base_id: knowledgeBaseId,
    top_k: 5,
    score_threshold: 0.5,
    result_count: 1,
    used_source_count: 1,
    context_characters: 128,
  },
  provider: "mock",
  model: "mock-model",
  usage: {
    input_tokens: 80,
    output_tokens: 12,
    total_tokens: 92,
  },
  llm_call_id: "00000000-0000-0000-0000-000000000408",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("RAG API", () => {
  it("posts the exact retrieval-only request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json(queryResponse, { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(queryKnowledgeBase(queryRequest)).resolves.toEqual(
      queryResponse,
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/rag/query",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(queryRequest),
      },
    );
  });

  it("posts the exact chat request with client lifecycle cancellation", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json(chatResponse, { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await expect(
      createRagChat(chatRequest, { signal: controller.signal }),
    ).resolves.toEqual(chatResponse);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/rag/chat",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(chatRequest),
        signal: controller.signal,
      },
    );
  });

  it("uses the safe structured backend error message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json(
          {
            error: {
              code: "knowledge_base_not_found",
              message: "Knowledge Base not found",
              request_id: "request-rag-1",
            },
          },
          { status: 404 },
        ),
      ),
    );

    await expect(createRagChat(chatRequest)).rejects.toThrow(
      "Knowledge Base not found",
    );
  });

  it("normalizes transport failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("private")));

    await expect(queryKnowledgeBase(queryRequest)).rejects.toThrow(
      "Unable to reach RAG API",
    );
  });

  it("normalizes invalid successful JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not-json", { status: 200 })),
    );

    await expect(createRagChat(chatRequest)).rejects.toThrow(
      "RAG API returned invalid JSON",
    );
  });

  it("falls back to status for a non-JSON failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("private upstream", { status: 502 }),
      ),
    );

    await expect(queryKnowledgeBase(queryRequest)).rejects.toThrow(
      "Request failed with status 502",
    );
  });
});
