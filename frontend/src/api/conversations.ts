import { getJson } from "./client";
import type { ApiMessage } from "../types/chat";
import type { ConversationSummary } from "../types/conversations";

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
