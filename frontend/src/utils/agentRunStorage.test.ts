import { describe, expect, it } from "vitest";

import {
  clearStoredAgentRunId,
  readStoredAgentRunId,
  storeAgentRunId,
} from "./agentRunStorage";

const runId = "00000000-0000-0000-0000-000000000101";

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear() {
      values.clear();
    },
    getItem(key: string) {
      return values.get(key) ?? null;
    },
    key(index: number) {
      return [...values.keys()][index] ?? null;
    },
    removeItem(key: string) {
      values.delete(key);
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
  };
}

describe("Agent run session storage", () => {
  it("stores, reads, and clears a valid run UUID", () => {
    const storage = createMemoryStorage();

    storeAgentRunId(storage, runId);
    expect(readStoredAgentRunId(storage)).toBe(runId);

    clearStoredAgentRunId(storage);
    expect(readStoredAgentRunId(storage)).toBeNull();
  });

  it("rejects a non-UUID before writing it", () => {
    const storage = createMemoryStorage();

    expect(() => storeAgentRunId(storage, "not-a-run-id")).toThrow(
      "valid UUID",
    );
    expect(storage.length).toBe(0);
  });

  it("removes an invalid stored value instead of returning it", () => {
    const storage = createMemoryStorage();
    storage.setItem("ai-agent-lab:last-agent-run-id", "private-invalid-value");

    expect(readStoredAgentRunId(storage)).toBeNull();
    expect(storage.length).toBe(0);
  });

  it("does not break the Agent flow when session storage is unavailable", () => {
    const storage = createMemoryStorage();
    storage.getItem = () => {
      throw new DOMException("Storage is disabled", "SecurityError");
    };
    storage.setItem = () => {
      throw new DOMException("Storage is disabled", "SecurityError");
    };
    storage.removeItem = () => {
      throw new DOMException("Storage is disabled", "SecurityError");
    };

    expect(readStoredAgentRunId(storage)).toBeNull();
    expect(() => storeAgentRunId(storage, runId)).not.toThrow();
    expect(() => clearStoredAgentRunId(storage)).not.toThrow();
  });
});
