export type ChatRole = "user" | "assistant" | "system";

export type ApiMessage = {
  id: string;
  conversation_id: string;
  role: ChatRole;
  content: string;
  model: string | null;
  provider: string | null;
  created_at: string;
};

export type TokenUsage = {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
};

export type ChatCompletionRequest = {
  conversation_id: string | null;
  provider: string;
  model: string;
  content: string;
  temperature?: number;
  max_tokens?: number | null;
};

export type ChatCompletionResponse = {
  conversation_id: string;
  user_message: ApiMessage;
  assistant_message: ApiMessage;
  provider: string;
  model: string;
  usage: TokenUsage | null;
  llm_call_id: string;
};

export type UiMessageStatus = "complete" | "streaming" | "stopped" | "error";

export type UiChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: UiMessageStatus;
};
