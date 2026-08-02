// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/knowledge", () => ({
  createKnowledgeBase: vi.fn(),
  fetchKnowledgeBases: vi.fn(),
  uploadKnowledgeDocument: vi.fn(),
}));
vi.mock("../api/health", () => ({ fetchHealth: vi.fn() }));

import { fetchHealth } from "../api/health";
import {
  createKnowledgeBase,
  fetchKnowledgeBases,
  uploadKnowledgeDocument,
} from "../api/knowledge";
import type {
  KnowledgeBase,
  KnowledgeDocument,
} from "../types/knowledge";
import KnowledgeBasePage from "./KnowledgeBasePage";

const knowledgeBases: KnowledgeBase[] = [
  {
    id: "00000000-0000-0000-0000-000000000301",
    name: "Engineering notes",
    description: "Architecture and runbooks",
    embedding_provider: null,
    embedding_model: null,
    vector_store: "qdrant",
    vector_collection_name: null,
    created_at: "2026-08-02T10:00:00",
    updated_at: "2026-08-02T10:00:00",
  },
  {
    id: "00000000-0000-0000-0000-000000000302",
    name: "Research",
    description: null,
    embedding_provider: "mock",
    embedding_model: "embedding-v1",
    vector_store: "qdrant",
    vector_collection_name: "research",
    created_at: "2026-08-02T09:00:00",
    updated_at: "2026-08-02T09:00:00",
  },
];

const readyDocument: KnowledgeDocument = {
  id: "00000000-0000-0000-0000-000000000304",
  knowledge_base_id: knowledgeBases[0].id,
  filename: "00000000-0000-0000-0000-000000000304.md",
  original_filename: "release-notes.md",
  file_type: "md",
  file_path:
    "00000000-0000-0000-0000-000000000301/00000000-0000-0000-0000-000000000304.md",
  file_size: 128,
  file_hash: "b".repeat(64),
  parse_status: "parsed",
  chunk_status: "chunked",
  embedding_status: "ready",
  error_message: null,
  metadata: { source: "upload" },
  created_at: "2026-08-02T10:05:00",
  updated_at: "2026-08-02T10:05:01",
};

const reactTestEnvironment = globalThis as typeof globalThis & {
  IS_REACT_ACT_ENVIRONMENT: boolean;
};

async function flushEffects(): Promise<void> {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

function mountPage(): { container: HTMLDivElement; root: Root } {
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  act(() => {
    root.render(<KnowledgeBasePage onSelectWorkspace={vi.fn()} />);
  });
  return { container, root };
}

function setControlValue(
  control: HTMLInputElement | HTMLTextAreaElement,
  value: string,
): void {
  const prototype =
    control instanceof HTMLInputElement
      ? HTMLInputElement.prototype
      : HTMLTextAreaElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
  setter?.call(control, value);
  control.dispatchEvent(new Event("input", { bubbles: true }));
}

function selectFile(input: HTMLInputElement, file: File): void {
  Object.defineProperty(input, "files", {
    configurable: true,
    value: [file],
  });
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function uploadControls(container: HTMLElement): {
  form: HTMLFormElement;
  input: HTMLInputElement;
} {
  const form = container.querySelector('form[aria-label="Upload document"]');
  const input = form?.querySelector('input[type="file"]');
  if (!(form instanceof HTMLFormElement) || !(input instanceof HTMLInputElement)) {
    throw new Error("Document upload form is missing");
  }
  return { form, input };
}

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

beforeEach(() => {
  reactTestEnvironment.IS_REACT_ACT_ENVIRONMENT = true;
  window.history.replaceState(null, "", "/?workspace=knowledge");
  vi.mocked(fetchHealth).mockResolvedValue({
    status: "ok",
    service: "AI Agent Lab Backend",
  });
  vi.mocked(fetchKnowledgeBases).mockResolvedValue(knowledgeBases);
  vi.mocked(createKnowledgeBase).mockReset();
  vi.mocked(uploadKnowledgeDocument).mockReset();
});

afterEach(() => {
  document.body.replaceChildren();
  vi.clearAllMocks();
});

describe("KnowledgeBasePage list and create flows", () => {
  it("prevents a create request while the initial list still owns selection", async () => {
    vi.mocked(fetchKnowledgeBases).mockReturnValue(
      deferred<KnowledgeBase[]>().promise,
    );
    const { container, root } = mountPage();
    await flushEffects();

    const name = container.querySelector('input[name="name"]');
    expect(name).toBeInstanceOf(HTMLInputElement);
    expect((name as HTMLInputElement).disabled).toBe(true);
    act(() => root.unmount());
  });

  it("loads Knowledge Bases and selects the first row", async () => {
    const { container, root } = mountPage();
    expect(container.textContent).toContain("Loading Knowledge Bases...");

    await flushEffects();

    expect(fetchKnowledgeBases).toHaveBeenCalledTimes(1);
    expect(container.textContent).toContain("Engineering notes");
    expect(container.textContent).toContain("Research");
    const selected = container.querySelector(
      '[aria-label="Select Engineering notes"]',
    );
    expect(selected?.getAttribute("aria-current")).toBe("true");
    expect(container.textContent).toContain("Architecture and runbooks");
    act(() => root.unmount());
  });

  it("shows the empty state when no Knowledge Base exists", async () => {
    vi.mocked(fetchKnowledgeBases).mockResolvedValueOnce([]);
    const { container, root } = mountPage();
    await flushEffects();

    expect(container.textContent).toContain("No Knowledge Bases yet");
    expect(container.textContent).toContain(
      "Create one to start ingesting documents.",
    );
    act(() => root.unmount());
  });

  it("retries a safe list failure", async () => {
    vi.mocked(fetchKnowledgeBases)
      .mockRejectedValueOnce(new Error("Unable to load Knowledge Bases"))
      .mockResolvedValueOnce(knowledgeBases);
    const { container, root } = mountPage();
    await flushEffects();

    expect(container.textContent).toContain("Unable to load Knowledge Bases");
    const retry = [...container.querySelectorAll("button")].find(
      (button) => button.textContent?.trim() === "Retry",
    );
    expect(retry).toBeDefined();
    await act(async () => {
      retry?.click();
      await Promise.resolve();
    });
    await flushEffects();

    expect(fetchKnowledgeBases).toHaveBeenCalledTimes(2);
    expect(container.textContent).toContain("Engineering notes");
    act(() => root.unmount());
  });

  it("creates, inserts, and selects a trimmed Knowledge Base", async () => {
    const created: KnowledgeBase = {
      ...knowledgeBases[0],
      id: "00000000-0000-0000-0000-000000000303",
      name: "Release notes",
      description: "Verified builds",
    };
    vi.mocked(createKnowledgeBase).mockResolvedValue(created);
    const { container, root } = mountPage();
    await flushEffects();

    const form = container.querySelector(
      'form[aria-label="Create Knowledge Base"]',
    );
    const name = form?.querySelector('input[name="name"]');
    const description = form?.querySelector('textarea[name="description"]');
    if (
      form === null ||
      !(name instanceof HTMLInputElement) ||
      !(description instanceof HTMLTextAreaElement)
    ) {
      throw new Error("Create Knowledge Base form is missing");
    }
    act(() => {
      setControlValue(name, "  Release notes  ");
      setControlValue(description, "  Verified builds  ");
    });
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });
    await flushEffects();

    expect(createKnowledgeBase).toHaveBeenCalledWith({
      name: "Release notes",
      description: "Verified builds",
    });
    const selected = container.querySelector(
      '[aria-label="Select Release notes"]',
    );
    expect(selected?.getAttribute("aria-current")).toBe("true");
    expect(container.textContent).toContain("Verified builds");
    act(() => root.unmount());
  });

  it("preserves creation input after a safe failure", async () => {
    vi.mocked(createKnowledgeBase).mockRejectedValue(
      new Error("Knowledge Base name is already in use"),
    );
    const { container, root } = mountPage();
    await flushEffects();

    const form = container.querySelector(
      'form[aria-label="Create Knowledge Base"]',
    );
    const name = form?.querySelector('input[name="name"]');
    if (form === null || !(name instanceof HTMLInputElement)) {
      throw new Error("Create Knowledge Base form is missing");
    }
    act(() => setControlValue(name, "Duplicate"));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });
    await flushEffects();

    expect(container.textContent).toContain(
      "Knowledge Base name is already in use",
    );
    expect(name.value).toBe("Duplicate");
    act(() => root.unmount());
  });

  it("disables list retry while a create request owns the list state", async () => {
    const pending = deferred<KnowledgeBase>();
    vi.mocked(fetchKnowledgeBases).mockRejectedValueOnce(
      new Error("Unable to load Knowledge Bases"),
    );
    vi.mocked(createKnowledgeBase).mockReturnValue(pending.promise);
    const { container, root } = mountPage();
    await flushEffects();

    const form = container.querySelector(
      'form[aria-label="Create Knowledge Base"]',
    );
    const name = form?.querySelector('input[name="name"]');
    if (form === null || !(name instanceof HTMLInputElement)) {
      throw new Error("Create Knowledge Base form is missing");
    }
    act(() => setControlValue(name, "Recovery notes"));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });

    const retry = [...container.querySelectorAll("button")].find(
      (button) => button.textContent?.trim() === "Retry",
    );
    expect((retry as HTMLButtonElement).disabled).toBe(true);

    await act(async () => {
      pending.resolve({ ...knowledgeBases[0], name: "Recovery notes" });
      await pending.promise;
    });
    act(() => root.unmount());
  });
});

describe("KnowledgeBasePage document upload flow", () => {
  it("accepts a supported file for the selected Knowledge Base", async () => {
    vi.mocked(uploadKnowledgeDocument).mockResolvedValue(readyDocument);
    const { container, root } = mountPage();
    await flushEffects();
    const { form, input } = uploadControls(container);
    expect(input.getAttribute("aria-describedby")).toBe(
      "document-upload-help",
    );
    const file = new File(["# Release notes"], "release-notes.MD", {
      type: "text/markdown",
    });

    act(() => selectFile(input, file));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });
    await flushEffects();

    expect(uploadKnowledgeDocument).toHaveBeenCalledWith(
      knowledgeBases[0].id,
      file,
    );
    expect(container.textContent).toContain("release-notes.md");
    expect(
      container.querySelector('[aria-label="Parse status: parsed"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[aria-label="Chunk status: chunked"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[aria-label="Embedding status: ready"]'),
    ).not.toBeNull();
    expect(container.textContent).toContain(readyDocument.id);
    expect(container.textContent).not.toContain(readyDocument.file_path);
    expect(container.textContent).not.toContain(readyDocument.file_hash);
    act(() => root.unmount());
  });

  it("rejects an unsupported filename before calling the API", async () => {
    const { container, root } = mountPage();
    await flushEffects();
    const { input } = uploadControls(container);

    act(() => selectFile(input, new File(["binary"], "notes.docx")));

    expect(container.textContent).toContain(
      "Only .md, .txt, and .pdf files are supported",
    );
    expect(uploadKnowledgeDocument).not.toHaveBeenCalled();
    act(() => root.unmount());
  });

  it("renders a processing-failure Document returned with HTTP 201", async () => {
    vi.mocked(uploadKnowledgeDocument).mockResolvedValue({
      ...readyDocument,
      parse_status: "failed",
      chunk_status: "pending",
      embedding_status: "pending",
      error_message: "Document parsing failed",
    });
    const { container, root } = mountPage();
    await flushEffects();
    const { form, input } = uploadControls(container);

    act(() => selectFile(input, new File(["broken"], "broken.pdf")));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });
    await flushEffects();

    expect(container.textContent).toContain("Document parsing failed");
    expect(
      container.querySelector('[aria-label="Parse status: failed"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[aria-label="Chunk status: pending"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[aria-label="Embedding status: pending"]'),
    ).not.toBeNull();
    act(() => root.unmount());
  });

  it("shows a safe upload request error and preserves the chosen file", async () => {
    vi.mocked(uploadKnowledgeDocument).mockRejectedValue(
      new Error("This document already exists in the knowledge base"),
    );
    const { container, root } = mountPage();
    await flushEffects();
    const { form, input } = uploadControls(container);
    const file = new File(["same"], "same.txt");

    act(() => selectFile(input, file));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });
    await flushEffects();

    expect(container.textContent).toContain(
      "This document already exists in the knowledge base",
    );
    expect(container.textContent).toContain("same.txt");
    act(() => root.unmount());
  });

  it("clears a stale request error when a different file is selected", async () => {
    vi.mocked(uploadKnowledgeDocument).mockRejectedValue(
      new Error("This document already exists in the knowledge base"),
    );
    const { container, root } = mountPage();
    await flushEffects();
    const { form, input } = uploadControls(container);

    act(() => selectFile(input, new File(["same"], "same.txt")));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });
    await flushEffects();
    expect(container.textContent).toContain(
      "This document already exists in the knowledge base",
    );

    act(() => selectFile(input, new File(["new"], "new.txt")));

    expect(container.textContent).not.toContain(
      "This document already exists in the knowledge base",
    );
    expect(container.textContent).toContain("new.txt");
    act(() => root.unmount());
  });

  it("disables conflicting controls while an upload is pending", async () => {
    const pending = deferred<KnowledgeDocument>();
    vi.mocked(uploadKnowledgeDocument).mockReturnValue(pending.promise);
    const { container, root } = mountPage();
    await flushEffects();
    const { form, input } = uploadControls(container);

    act(() => selectFile(input, new File(["notes"], "notes.txt")));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });

    const createName = container.querySelector('input[name="name"]');
    const selectedKnowledgeBase = container.querySelector(
      '[aria-label="Select Engineering notes"]',
    );
    expect(container.textContent).toContain("Uploading...");
    expect(form.getAttribute("aria-busy")).toBe("true");
    expect((createName as HTMLInputElement).disabled).toBe(true);
    expect((selectedKnowledgeBase as HTMLButtonElement).disabled).toBe(true);

    await act(async () => {
      pending.resolve(readyDocument);
      await pending.promise;
    });
    await flushEffects();
    act(() => root.unmount());
  });

  it("clears the uploaded Document when selecting another owner", async () => {
    vi.mocked(uploadKnowledgeDocument).mockResolvedValue(readyDocument);
    const { container, root } = mountPage();
    await flushEffects();
    const { form, input } = uploadControls(container);

    act(() => selectFile(input, new File(["notes"], "release-notes.md")));
    await act(async () => {
      form.dispatchEvent(
        new Event("submit", { bubbles: true, cancelable: true }),
      );
      await Promise.resolve();
    });
    await flushEffects();
    expect(container.textContent).toContain(readyDocument.id);

    const research = container.querySelector(
      '[aria-label="Select Research"]',
    );
    act(() => (research as HTMLButtonElement).click());

    expect(container.textContent).not.toContain(readyDocument.id);
    expect(container.textContent).toContain("Research");
    act(() => root.unmount());
  });
});
