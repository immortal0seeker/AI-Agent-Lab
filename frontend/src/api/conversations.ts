import {
  API_BASE_URL,
  createApiUrl,
  getJson,
  readResponseError,
} from "./client";
import type { ApiMessage } from "../types/chat";
import type {
  ConversationCreate,
  ConversationSummary,
} from "../types/conversations";

export async function createConversation(
  request: ConversationCreate,
): Promise<ConversationSummary> {
  let response: Response;
  try {
    response = await fetch(createApiUrl(API_BASE_URL, "/conversations"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    throw new Error("Unable to reach Conversation API");
  }

  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }

  try {
    return (await response.json()) as ConversationSummary;
  } catch {
    throw new Error("Conversation API returned invalid JSON");
  }
}

export function fetchConversations(): Promise<ConversationSummary[]> {
  return getJson<ConversationSummary[]>("/conversations");
}

export function fetchConversationMessages(
  conversationId: string,
): Promise<ApiMessage[]> {
  return getJson<ApiMessage[]>(
    `/conversations/${encodeURIComponent(conversationId)}/messages`,
  );
}
