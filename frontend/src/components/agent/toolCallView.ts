import type {
  ToolCallStatus,
  ToolResult,
} from "../../types/agent";

export type ToolCallTone = "pending" | "success" | "error";

export type ToolResultSection = {
  label: "Content" | "Data" | "Metadata" | "Error";
  value: string;
  tone: "normal" | "error";
};

export function toolCallTone(status: ToolCallStatus): ToolCallTone {
  if (status === "success") {
    return "success";
  }
  if (status === "pending" || status === "running") {
    return "pending";
  }
  return "error";
}

export function formatLatency(latencyMs: number | null): string {
  if (latencyMs === null) {
    return "Not recorded";
  }
  if (latencyMs < 1000) {
    return `${latencyMs} ms`;
  }
  return `${(latencyMs / 1000).toFixed(2)} s`;
}

function sortJson(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(sortJson);
  }
  if (typeof value === "object" && value !== null) {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, nested]) => [key, sortJson(nested)]),
    );
  }
  return value;
}

export function formatJson(value: unknown): string {
  return JSON.stringify(sortJson(value), null, 2) ?? String(value);
}

export function summarizeText(text: string, limit = 600): string {
  if (text.length <= limit) {
    return text;
  }
  if (limit <= 0) {
    return "";
  }
  if (limit === 1) {
    return "…";
  }
  return `${text.slice(0, limit - 1)}…`;
}

export function toolResultSections(
  result: ToolResult,
): ToolResultSection[] {
  const sections: ToolResultSection[] = [];
  if (result.content.trim()) {
    sections.push({
      label: "Content",
      value: summarizeText(result.content),
      tone: "normal",
    });
  }
  if (result.data !== null) {
    sections.push({
      label: "Data",
      value: summarizeText(formatJson(result.data)),
      tone: "normal",
    });
  }
  if (Object.keys(result.metadata).length > 0) {
    sections.push({
      label: "Metadata",
      value: summarizeText(formatJson(result.metadata)),
      tone: "normal",
    });
  }
  if (result.error !== null) {
    sections.push({
      label: "Error",
      value: summarizeText(result.error),
      tone: "error",
    });
  }
  return sections;
}
