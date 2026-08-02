export type ConversationCreate = {
  title?: string;
  default_provider?: string | null;
  default_model?: string | null;
};

export type ConversationSummary = {
  id: string;
  title: string;
  default_provider: string | null;
  default_model: string | null;
  created_at: string;
  updated_at: string;
};
