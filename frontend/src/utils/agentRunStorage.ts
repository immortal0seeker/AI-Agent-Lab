const AGENT_RUN_STORAGE_KEY = "ai-agent-lab:last-agent-run-id";
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isValidRunId(value: string): boolean {
  return UUID_PATTERN.test(value);
}

export function readStoredAgentRunId(storage: Storage): string | null {
  let value: string | null;
  try {
    value = storage.getItem(AGENT_RUN_STORAGE_KEY);
  } catch {
    return null;
  }
  if (value === null) {
    return null;
  }
  if (!isValidRunId(value)) {
    try {
      storage.removeItem(AGENT_RUN_STORAGE_KEY);
    } catch {
      // 存储不可用时保持页面可用，恢复能力自然降级。
    }
    return null;
  }
  return value;
}

export function storeAgentRunId(storage: Storage, runId: string): void {
  if (!isValidRunId(runId)) {
    throw new Error("Agent run ID must be a valid UUID");
  }
  try {
    storage.setItem(AGENT_RUN_STORAGE_KEY, runId);
  } catch {
    // 隐私模式等环境可能禁用 sessionStorage，不应把成功运行改写成失败。
  }
}

export function clearStoredAgentRunId(storage: Storage): void {
  try {
    storage.removeItem(AGENT_RUN_STORAGE_KEY);
  } catch {
    // 与写入一致：存储不可用不阻断 Agent 工作流。
  }
}
