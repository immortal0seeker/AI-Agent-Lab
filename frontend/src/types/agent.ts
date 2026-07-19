export type AgentRunStatus =
  | "created"
  | "running"
  | "waiting_tool"
  | "completed"
  | "failed"
  | "cancelled";

export type ToolCallStatus =
  | "pending"
  | "running"
  | "success"
  | "failed"
  | "timeout"
  | "blocked";

export type ToolResult = {
  tool_name: string;
  success: boolean;
  content: string;
  data: Record<string, unknown> | null;
  error: string | null;
  metadata: Record<string, unknown>;
};

export type AgentRunCreate = {
  conversation_id?: string | null;
  provider: string;
  model: string;
  input: string;
  temperature?: number;
  max_tokens?: number | null;
  max_steps?: number;
};

export type AgentRun = {
  id: string;
  conversation_id: string;
  user_message_id: string | null;
  status: AgentRunStatus;
  goal: string;
  final_answer: string | null;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
  latency_ms: number | null;
  created_at: string;
};

export type ToolCall = {
  id: string;
  tool_call_id: string;
  agent_run_id: string;
  conversation_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: ToolResult | null;
  status: ToolCallStatus;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
  latency_ms: number | null;
  created_at: string;
};

export type AgentRunExecution = AgentRun & {
  tool_calls: ToolCall[];
};
