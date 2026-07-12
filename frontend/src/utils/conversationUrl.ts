const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function readConversationId(search: string): string | null {
  const conversationId = new URLSearchParams(search).get("conversation");
  return conversationId !== null && UUID_PATTERN.test(conversationId)
    ? conversationId
    : null;
}

export function buildConversationUrl(
  href: string,
  conversationId: string | null,
): string {
  const url = new URL(href);
  if (conversationId === null) {
    url.searchParams.delete("conversation");
  } else {
    url.searchParams.set("conversation", conversationId);
  }
  return url.toString();
}
