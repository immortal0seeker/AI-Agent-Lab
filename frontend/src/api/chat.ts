import {
  API_BASE_URL,
  apiErrorMessage,
  createApiUrl,
  readResponseError,
} from "./client";
import type {
  ChatCompletionRequest,
  ChatCompletionResponse,
} from "../types/chat";

type StreamChatOptions = {
  signal?: AbortSignal;
  onDelta: (content: string) => void;
};

type SseFrame = {
  event: string;
  data: unknown;
};

function parseFrame(frame: string): SseFrame | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    event,
    data: JSON.parse(dataLines.join("\n")) as unknown,
  };
}

function takeFrames(buffer: string): { frames: string[]; rest: string } {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const parts = normalized.split("\n\n");
  const rest = parts.pop() ?? "";
  return { frames: parts, rest };
}

export async function streamChat(
  request: ChatCompletionRequest,
  options: StreamChatOptions,
): Promise<ChatCompletionResponse> {
  const response = await fetch(createApiUrl(API_BASE_URL, "/chat/stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal: options.signal,
  });

  if (!response.ok) {
    throw new Error(await readResponseError(response));
  }
  if (response.body === null) {
    throw new Error("Streaming response body is unavailable");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed: ChatCompletionResponse | null = null;

  const handleFrame = (rawFrame: string) => {
    const frame = parseFrame(rawFrame);
    if (frame === null) {
      return;
    }
    if (frame.event === "delta") {
      const payload = frame.data as { content?: unknown };
      if (typeof payload.content !== "string") {
        throw new Error("Invalid delta event payload");
      }
      options.onDelta(payload.content);
    } else if (frame.event === "done") {
      completed = frame.data as ChatCompletionResponse;
    } else if (frame.event === "error") {
      throw new Error(apiErrorMessage(frame.data, "Streaming request failed"));
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const parsed = takeFrames(buffer);
      buffer = parsed.rest;
      for (const frame of parsed.frames) {
        handleFrame(frame);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      handleFrame(buffer.replace(/\r\n/g, "\n"));
    }

    if (completed === null) {
      throw new Error("Stream ended before a terminal event");
    }
    return completed;
  } finally {
    try {
      await reader.cancel();
    } catch {
      // Abort 后 cancel 也可能失败，不能让清理异常覆盖原始流错误。
    }
    reader.releaseLock();
  }
}
