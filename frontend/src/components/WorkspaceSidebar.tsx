import { Activity, History, MessageSquarePlus, X } from "lucide-react";
import { useState } from "react";

import { API_BASE_URL } from "../api/client";
import type { ConversationSummary } from "../types/conversations";
import ConversationList from "./ConversationList";

export type ApiHealth =
  | { status: "checking" }
  | { status: "healthy"; service: string }
  | { status: "error"; message: string };

type WorkspaceSidebarProps = {
  health: ApiHealth;
  conversations: ConversationSummary[];
  selectedConversationId: string | null;
  conversationsLoading: boolean;
  navigationDisabled: boolean;
  onNewChat: () => void;
  onSelectConversation: (conversationId: string) => void;
};

export default function WorkspaceSidebar({
  health,
  conversations,
  selectedConversationId,
  conversationsLoading,
  navigationDisabled,
  onNewChat,
  onSelectConversation,
}: WorkspaceSidebarProps) {
  const [mobileHistoryOpen, setMobileHistoryOpen] = useState(false);
  const healthLabel =
    health.status === "checking"
      ? "Checking API"
      : health.status === "healthy"
        ? "API connected"
        : "API unavailable";
  const selectConversation = (conversationId: string) => {
    setMobileHistoryOpen(false);
    onSelectConversation(conversationId);
  };
  const startNewChat = () => {
    setMobileHistoryOpen(false);
    onNewChat();
  };

  return (
    <aside className="workspace-sidebar">
      <div className="brand-block">
        <span className="brand-mark" aria-hidden="true">
          AI
        </span>
        <div>
          <strong>AI Agent Lab</strong>
          <span>Engineering Workspace</span>
        </div>
      </div>

      <button
        className="new-chat-button"
        type="button"
        title="New chat"
        aria-label="New chat"
        onClick={startNewChat}
      >
        <MessageSquarePlus size={17} aria-hidden="true" />
        <span>New chat</span>
      </button>

      <button
        className="mobile-history-button"
        type="button"
        title="Conversation history"
        aria-label="Conversation history"
        aria-expanded={mobileHistoryOpen}
        aria-controls="mobile-conversation-history"
        onClick={() => setMobileHistoryOpen((open) => !open)}
      >
        <History size={17} aria-hidden="true" />
      </button>

      <section className="conversation-region" aria-labelledby="history-heading">
        <h2 id="history-heading">Recent</h2>
        <ConversationList
          conversations={conversations}
          selectedId={selectedConversationId}
          isLoading={conversationsLoading}
          disabled={navigationDisabled}
          onSelect={selectConversation}
        />
      </section>

      {mobileHistoryOpen ? (
        <section
          id="mobile-conversation-history"
          className="mobile-history-panel"
          aria-label="Conversation history"
        >
          <header>
            <strong>Recent conversations</strong>
            <button
              type="button"
              title="Close conversation history"
              aria-label="Close conversation history"
              onClick={() => setMobileHistoryOpen(false)}
            >
              <X size={16} aria-hidden="true" />
            </button>
          </header>
          <ConversationList
            conversations={conversations}
            selectedId={selectedConversationId}
            isLoading={conversationsLoading}
            disabled={navigationDisabled}
            onSelect={selectConversation}
          />
        </section>
      ) : null}

      <section className="api-status" aria-label="Backend API status">
        <div className="api-status-heading">
          <Activity size={15} aria-hidden="true" />
          <span>Backend API</span>
        </div>
        <div className={`health-line health-line--${health.status}`}>
          <span className="health-dot" aria-hidden="true" />
          <span>{healthLabel}</span>
        </div>
        <code title={API_BASE_URL}>{API_BASE_URL}</code>
        {health.status === "error" ? (
          <p className="health-detail" title={health.message}>
            {health.message}
          </p>
        ) : null}
      </section>
    </aside>
  );
}
