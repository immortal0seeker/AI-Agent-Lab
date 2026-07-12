import { describe, expect, it } from "vitest";

import { buildConversationUrl, readConversationId } from "./conversationUrl";

const CONVERSATION_ID = "4a36e703-b5c3-4b07-914b-e12f5187473a";

describe("conversation URL helpers", () => {
  it("reads a valid UUID conversation query", () => {
    expect(readConversationId(`?conversation=${CONVERSATION_ID}`)).toBe(
      CONVERSATION_ID,
    );
  });

  it("rejects invalid conversation query text", () => {
    expect(readConversationId("?conversation=not-a-uuid")).toBeNull();
  });

  it("adds a conversation while preserving query and hash", () => {
    expect(
      buildConversationUrl(
        "http://localhost:5173/?tab=chat#messages",
        CONVERSATION_ID,
      ),
    ).toBe(
      `http://localhost:5173/?tab=chat&conversation=${CONVERSATION_ID}#messages`,
    );
  });

  it("replaces and removes the selected conversation", () => {
    const replaced = buildConversationUrl(
      "http://localhost:5173/?conversation=old&tab=chat",
      CONVERSATION_ID,
    );

    expect(replaced).toBe(
      `http://localhost:5173/?conversation=${CONVERSATION_ID}&tab=chat`,
    );
    expect(buildConversationUrl(replaced, null)).toBe(
      "http://localhost:5173/?tab=chat",
    );
  });
});
