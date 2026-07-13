import { afterEach, describe, expect, it, vi } from "vitest";

import { streamChat } from "./chat";
import type { ChatCompletionResponse } from "../types/chat";

const doneResponse: ChatCompletionResponse = {
  conversation_id: "conversation-1",
  user_message: {
    id: "user-1",
    conversation_id: "conversation-1",
    role: "user",
    content: "Hello",
    model: null,
    provider: null,
    created_at: "2026-07-12T12:00:00",
  },
  assistant_message: {
    id: "assistant-1",
    conversation_id: "conversation-1",
    role: "assistant",
    content: "Hello back",
    model: "example-model",
    provider: "openai_compatible",
    created_at: "2026-07-12T12:00:01",
  },
  provider: "openai_compatible",
  model: "example-model",
  usage: { input_tokens: 2, output_tokens: 2, total_tokens: 4 },
  llm_call_id: "call-1",
};

function createStreamResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("streamChat", () => {
  it("parses split delta and done SSE frames", async () => {
    const doneFrame = `event: done\r\ndata: ${JSON.stringify(doneResponse)}\r\n\r\n`;
    const fetchMock = vi.fn().mockResolvedValue(
      createStreamResponse([
        'event: delta\ndata: {"cont',
        'ent":"Hello "}\n\nevent: delta\ndata: {"content":"back"}\n\n',
        doneFrame.slice(0, 35),
        doneFrame.slice(35),
      ]),
    );
    vi.stubGlobal("fetch", fetchMock);
    const deltas: string[] = [];
    const controller = new AbortController();

    const result = await streamChat(
      {
        conversation_id: null,
        provider: "openai_compatible",
        model: "example-model",
        content: "Hello",
      },
      {
        signal: controller.signal,
        onDelta: (content) => deltas.push(content),
      },
    );

    expect(deltas).toEqual(["Hello ", "back"]);
    expect(result).toEqual(doneResponse);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/chat/stream",
      expect.objectContaining({
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
      }),
    );
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      conversation_id: null,
      provider: "openai_compatible",
      model: "example-model",
      content: "Hello",
    });
  });

  it("rejects a terminal SSE error event", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        createStreamResponse([
          'event: error\ndata: {"error":{"code":"provider_timeout","message":"The model provider timed out","request_id":"request-1"}}\n\n',
        ]),
      ),
    );

    await expect(
      streamChat(
        {
          conversation_id: null,
          provider: "openai_compatible",
          model: "example-model",
          content: "Hello",
        },
        { onDelta: () => undefined },
      ),
    ).rejects.toThrow("The model provider timed out");
  });

  it("cancels the response reader after a terminal SSE error", async () => {
    const encoder = new TextEncoder();
    const cancel = vi.fn();
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            'event: error\ndata: {"error":{"message":"Provider unavailable"}}\n\n',
          ),
        );
      },
      cancel,
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(body, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      ),
    );

    await expect(
      streamChat(
        {
          conversation_id: null,
          provider: "openai_compatible",
          model: "example-model",
          content: "Hello",
        },
        { onDelta: () => undefined },
      ),
    ).rejects.toThrow("Provider unavailable");
    expect(cancel).toHaveBeenCalledOnce();
  });

  it("keeps compatibility with a legacy SSE error message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        createStreamResponse([
          'event: error\ndata: {"message":"Provider unavailable"}\n\n',
        ]),
      ),
    );

    await expect(
      streamChat(
        {
          conversation_id: null,
          provider: "openai_compatible",
          model: "example-model",
          content: "Hello",
        },
        { onDelta: () => undefined },
      ),
    ).rejects.toThrow("Provider unavailable");
  });

  it("rejects a stream that closes without a terminal event", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        createStreamResponse([
          'event: delta\ndata: {"content":"partial"}\n\n',
        ]),
      ),
    );

    await expect(
      streamChat(
        {
          conversation_id: null,
          provider: "openai_compatible",
          model: "example-model",
          content: "Hello",
        },
        { onDelta: () => undefined },
      ),
    ).rejects.toThrow("Stream ended before a terminal event");
  });

  it("uses the backend detail for an HTTP error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "API key is required" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(
      streamChat(
        {
          conversation_id: null,
          provider: "openai_compatible",
          model: "example-model",
          content: "Hello",
        },
        { onDelta: () => undefined },
      ),
    ).rejects.toThrow("API key is required");
  });

  it("uses the structured backend error for an HTTP failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "provider_unavailable",
              message: "The model provider is not configured",
              request_id: "request-2",
            },
          }),
          {
            status: 503,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );

    await expect(
      streamChat(
        {
          conversation_id: null,
          provider: "openai_compatible",
          model: "example-model",
          content: "Hello",
        },
        { onDelta: () => undefined },
      ),
    ).rejects.toThrow("The model provider is not configured");
  });
});
