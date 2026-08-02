import {
  API_BASE_URL,
  createApiUrl,
  readResponseError,
} from "./client";
import type {
  RagChatRequest,
  RagChatResponse,
  RagQueryResponse,
  RagRetrievalRequest,
} from "../types/rag";

type RagRequestOptions = {
  signal?: AbortSignal;
};

async function postRagJson<T>(
  path: string,
  request: unknown,
  options: RagRequestOptions = {},
): Promise<T> {
  const init: RequestInit = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  };
  if (options.signal !== undefined) {
    init.signal = options.signal;
  }

  let response: Response;
  try {
    response = await fetch(createApiUrl(API_BASE_URL, path), init);
  } catch {
    throw new Error("Unable to reach RAG API");
  }

  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new Error("RAG API returned invalid JSON");
  }
}

export function queryKnowledgeBase(
  request: RagRetrievalRequest,
): Promise<RagQueryResponse> {
  return postRagJson<RagQueryResponse>("/rag/query", request);
}

export function createRagChat(
  request: RagChatRequest,
  options: RagRequestOptions = {},
): Promise<RagChatResponse> {
  return postRagJson<RagChatResponse>("/rag/chat", request, options);
}
