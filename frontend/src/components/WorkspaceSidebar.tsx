import { Activity, MessageSquarePlus } from "lucide-react";

import { API_BASE_URL } from "../api/client";

export type ApiHealth =
  | { status: "checking" }
  | { status: "healthy"; service: string }
  | { status: "error"; message: string };

type WorkspaceSidebarProps = {
  health: ApiHealth;
  onNewChat: () => void;
};

export default function WorkspaceSidebar({
  health,
  onNewChat,
}: WorkspaceSidebarProps) {
  const healthLabel =
    health.status === "checking"
      ? "Checking API"
      : health.status === "healthy"
        ? "API connected"
        : "API unavailable";

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

      <button className="new-chat-button" type="button" onClick={onNewChat}>
        <MessageSquarePlus size={17} aria-hidden="true" />
        <span>New chat</span>
      </button>

      <div className="sidebar-spacer" />

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
