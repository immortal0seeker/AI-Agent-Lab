import { MessageSquare } from "lucide-react";

import type { ConversationSummary } from "../types/conversations";

type ConversationListProps = {
  conversations: ConversationSummary[];
  selectedId: string | null;
  isLoading: boolean;
  disabled: boolean;
  onSelect: (conversationId: string) => void;
};

const updatedAtFormatter = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

function formatUpdatedAt(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Unknown time"
    : updatedAtFormatter.format(date);
}

export default function ConversationList({
  conversations,
  selectedId,
  isLoading,
  disabled,
  onSelect,
}: ConversationListProps) {
  if (isLoading) {
    return (
      <div className="conversation-list-state" role="status">
        Loading conversations...
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="conversation-list-state">
        <MessageSquare size={17} aria-hidden="true" />
        <span>No saved conversations</span>
      </div>
    );
  }

  return (
    <nav className="conversation-list" aria-label="Conversations">
      {conversations.map((conversation) => (
        <button
          type="button"
          key={conversation.id}
          aria-current={selectedId === conversation.id ? "true" : undefined}
          disabled={disabled}
          onClick={() => onSelect(conversation.id)}
        >
          <span>{conversation.title}</span>
          <time dateTime={conversation.updated_at}>
            {formatUpdatedAt(conversation.updated_at)}
          </time>
        </button>
      ))}
    </nav>
  );
}
