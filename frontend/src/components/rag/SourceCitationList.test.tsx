// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import type { RagSource } from "../../types/rag";
import SourceCitationList from "./SourceCitationList";

const knowledgeBaseId = "00000000-0000-0000-0000-000000000701";

const sources: RagSource[] = [
  {
    source_index: 1,
    knowledge_base_id: knowledgeBaseId,
    document_id: "00000000-0000-0000-0000-000000000702",
    chunk_id: "00000000-0000-0000-0000-000000000703",
    embedding_provider: "openai_compatible",
    embedding_model: "text-embedding-3-small",
    filename: "architecture.md",
    chunk_index: 2,
    content: "Routes delegate business work to services.",
    score: 0.93214,
    heading: "Runtime boundaries",
    page_number: null,
    metadata: {
      source_format: "md",
      line_start: 18,
      nested: { reviewed: true },
    },
  },
  {
    source_index: 2,
    knowledge_base_id: knowledgeBaseId,
    document_id: "00000000-0000-0000-0000-000000000704",
    chunk_id: "00000000-0000-0000-0000-000000000705",
    embedding_provider: "openai_compatible",
    embedding_model: "text-embedding-3-small",
    filename: "manual.pdf",
    chunk_index: 5,
    content: "The local workspace keeps SQLite as the primary database.",
    score: 0.81234,
    heading: null,
    page_number: 3,
    metadata: { source_format: "pdf" },
  },
];

const reactTestEnvironment = globalThis as typeof globalThis & {
  IS_REACT_ACT_ENVIRONMENT: boolean;
};

function mountList(items: RagSource[]): {
  container: HTMLDivElement;
  root: Root;
} {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  act(() => {
    root.render(<SourceCitationList sources={items} />);
  });
  return { container, root };
}

beforeEach(() => {
  reactTestEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
});

afterEach(() => {
  document.body.replaceChildren();
});

describe("SourceCitationList", () => {
  it("renders sources in backend order with complete provenance", () => {
    const { container, root } = mountList(sources);
    const cards = [...container.querySelectorAll("article")];

    expect(cards).toHaveLength(2);
    expect(cards[0]?.getAttribute("aria-label")).toBe(
      "Source 1: architecture.md",
    );
    expect(cards[1]?.getAttribute("aria-label")).toBe("Source 2: manual.pdf");
    expect(cards[0]?.textContent).toContain("Routes delegate business work");
    expect(cards[0]?.textContent).toContain("0.9321");
    expect(cards[0]?.textContent).toContain("Runtime boundaries");
    expect(cards[0]?.textContent).toContain("Chunk 2");
    expect(cards[0]?.textContent).toContain(sources[0].document_id);
    expect(cards[0]?.textContent).toContain(sources[0].chunk_id);
    expect(cards[0]?.textContent).toContain("openai_compatible");
    expect(cards[0]?.textContent).toContain("text-embedding-3-small");
    expect(cards[0]?.textContent).toContain("source_format");
    expect(cards[0]?.textContent).toContain("md");
    expect(cards[0]?.textContent).toContain('{"reviewed":true}');
    expect(cards[1]?.textContent).toContain("Page 3");
    expect(cards[1]?.textContent).toContain("0.8123");
    act(() => root.unmount());
  });

  it("renders an explicit no-source result", () => {
    const { container, root } = mountList([]);

    expect(container.textContent).toContain("No sources were used");
    expect(container.querySelectorAll("article")).toHaveLength(0);
    act(() => root.unmount());
  });

  it("renders untrusted source content and metadata only as text", () => {
    const untrusted = '<img src=x onerror="globalThis.compromised=true">';
    const { container, root } = mountList([
      {
        ...sources[0],
        content: untrusted,
        metadata: { untrusted },
      },
    ]);

    expect(container.textContent).toContain(untrusted);
    expect(container.querySelector("img")).toBeNull();
    expect((globalThis as { compromised?: boolean }).compromised).toBeUndefined();
    act(() => root.unmount());
  });
});
