import {
  API_BASE_URL,
  createApiUrl,
  readResponseError,
} from "./client";
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
  KnowledgeDocument,
} from "../types/knowledge";

async function requestKnowledgeJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(createApiUrl(API_BASE_URL, path), init);
  } catch {
    throw new Error("Unable to reach Knowledge API");
  }

  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }

  try {
    return (await response.json()) as T;
  } catch {
    throw new Error("Knowledge API returned invalid JSON");
  }
}

export function fetchKnowledgeBases(): Promise<KnowledgeBase[]> {
  return requestKnowledgeJson<KnowledgeBase[]>("/knowledge-bases");
}

export function createKnowledgeBase(
  request: KnowledgeBaseCreate,
): Promise<KnowledgeBase> {
  return requestKnowledgeJson<KnowledgeBase>("/knowledge-bases", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export function uploadKnowledgeDocument(
  knowledgeBaseId: string,
  file: File,
): Promise<KnowledgeDocument> {
  const body = new FormData();
  body.append("file", file);

  return requestKnowledgeJson<KnowledgeDocument>(
    `/knowledge-bases/${encodeURIComponent(knowledgeBaseId)}/documents`,
    { method: "POST", body },
  );
}
