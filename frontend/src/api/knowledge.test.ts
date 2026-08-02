import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createKnowledgeBase,
  fetchKnowledgeBases,
  uploadKnowledgeDocument,
} from "./knowledge";
import type {
  KnowledgeBase,
  KnowledgeDocument,
} from "../types/knowledge";

const knowledgeBase: KnowledgeBase = {
  id: "00000000-0000-0000-0000-000000000201",
  name: "Product notes",
  description: "Plan 3 references",
  embedding_provider: null,
  embedding_model: null,
  vector_store: "qdrant",
  vector_collection_name: null,
  created_at: "2026-08-02T09:00:00",
  updated_at: "2026-08-02T09:00:00",
};

const document: KnowledgeDocument = {
  id: "00000000-0000-0000-0000-000000000202",
  knowledge_base_id: knowledgeBase.id,
  filename: "00000000-0000-0000-0000-000000000202.md",
  original_filename: "notes.md",
  file_type: "md",
  file_path:
    "00000000-0000-0000-0000-000000000201/00000000-0000-0000-0000-000000000202.md",
  file_size: 18,
  file_hash: "a".repeat(64),
  parse_status: "parsed",
  chunk_status: "chunked",
  embedding_status: "ready",
  error_message: null,
  metadata: {},
  created_at: "2026-08-02T09:01:00",
  updated_at: "2026-08-02T09:01:01",
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Knowledge API", () => {
  it("loads Knowledge Bases from the plural endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json([knowledgeBase], { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchKnowledgeBases()).resolves.toEqual([knowledgeBase]);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-bases",
      undefined,
    );
  });

  it("creates a Knowledge Base with the exact JSON request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json(knowledgeBase, { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      createKnowledgeBase({
        name: "Product notes",
        description: "Plan 3 references",
      }),
    ).resolves.toEqual(knowledgeBase);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/knowledge-bases",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Product notes",
          description: "Plan 3 references",
        }),
      },
    );
  });

  it("uploads one file without overriding the multipart boundary", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json(document, { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["# Product notes"], "Notes.MD", {
      type: "text/markdown",
    });

    await expect(
      uploadKnowledgeDocument("knowledge/base", file),
    ).resolves.toEqual(document);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(
      "http://localhost:8000/api/v1/knowledge-bases/knowledge%2Fbase/documents",
    );
    expect(init.method).toBe("POST");
    expect(init.headers).toBeUndefined();
    expect(init.body).toBeInstanceOf(FormData);
    expect((init.body as FormData).get("file")).toBe(file);
  });

  it("uses the safe structured backend error message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json(
          {
            error: {
              code: "document_duplicate",
              message: "This document already exists in the knowledge base",
              request_id: "request-knowledge-1",
            },
          },
          { status: 409 },
        ),
      ),
    );

    await expect(
      uploadKnowledgeDocument(knowledgeBase.id, new File(["same"], "same.txt")),
    ).rejects.toThrow("This document already exists in the knowledge base");
  });

  it("normalizes transport and invalid success JSON failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("private")));
    await expect(fetchKnowledgeBases()).rejects.toThrow(
      "Unable to reach Knowledge API",
    );

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("not-json", { status: 200 })),
    );
    await expect(fetchKnowledgeBases()).rejects.toThrow(
      "Knowledge API returned invalid JSON",
    );
  });

  it("falls back to status for a non-JSON failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("private upstream", { status: 502 })),
    );

    await expect(fetchKnowledgeBases()).rejects.toThrow(
      "Request failed with status 502",
    );
  });
});
