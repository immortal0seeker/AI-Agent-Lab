import { describe, expect, it } from "vitest";

import {
  formatJson,
  formatLatency,
  summarizeText,
  toolCallTone,
  toolResultSections,
} from "./toolCallView";
import type { ToolResult } from "../../types/agent";

describe("ToolCall view helpers", () => {
  it("maps every backend ToolCall status to a visual tone", () => {
    expect(toolCallTone("pending")).toBe("pending");
    expect(toolCallTone("running")).toBe("pending");
    expect(toolCallTone("success")).toBe("success");
    expect(toolCallTone("failed")).toBe("error");
    expect(toolCallTone("timeout")).toBe("error");
    expect(toolCallTone("blocked")).toBe("error");
  });

  it("formats missing, millisecond, and second latency explicitly", () => {
    expect(formatLatency(null)).toBe("Not recorded");
    expect(formatLatency(0)).toBe("0 ms");
    expect(formatLatency(23)).toBe("23 ms");
    expect(formatLatency(1200)).toBe("1.20 s");
  });

  it("sorts object keys recursively without changing array order", () => {
    expect(
      formatJson({ z: 1, nested: { b: 2, a: 1 }, list: [{ d: 4, c: 3 }], a: 0 }),
    ).toBe(
      '{\n  "a": 0,\n  "list": [\n    {\n      "c": 3,\n      "d": 4\n    }\n  ],\n  "nested": {\n    "a": 1,\n    "b": 2\n  },\n  "z": 1\n}',
    );
  });

  it("bounds text with an ellipsis while preserving the requested limit", () => {
    expect(summarizeText("123456", 5)).toBe("1234…");
    expect(summarizeText("1234", 5)).toBe("1234");
  });

  it("builds independent content, data, and metadata sections", () => {
    const result: ToolResult = {
      tool_name: "read_file",
      success: true,
      content: "README content",
      data: { lines: 20 },
      error: null,
      metadata: { path: "README.md" },
    };

    expect(toolResultSections(result)).toEqual([
      { label: "Content", value: "README content", tone: "normal" },
      { label: "Data", value: '{\n  "lines": 20\n}', tone: "normal" },
      {
        label: "Metadata",
        value: '{\n  "path": "README.md"\n}',
        tone: "normal",
      },
    ]);
    expect(result.metadata).toEqual({ path: "README.md" });
  });

  it("exposes a failed ToolResult error without inventing empty sections", () => {
    const result: ToolResult = {
      tool_name: "read_file",
      success: false,
      content: "",
      data: null,
      error: "File is blocked",
      metadata: {},
    };

    expect(toolResultSections(result)).toEqual([
      { label: "Error", value: "File is blocked", tone: "error" },
    ]);
  });
});
