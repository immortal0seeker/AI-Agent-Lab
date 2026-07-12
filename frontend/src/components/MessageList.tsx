import { Bot, CircleStop, MessageSquareText, UserRound } from "lucide-react";

import type { UiChatMessage } from "../types/chat";

type MessageListProps = {
  messages: UiChatMessage[];
};

export default function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="empty-chat">
        <MessageSquareText size={28} strokeWidth={1.5} aria-hidden="true" />
        <h2>Start a conversation</h2>
        <p>Send a message to the configured model.</p>
      </div>
    );
  }

  return (
    <div className="message-list" aria-live="polite">
      {messages.map((message) => (
        <article
          className={`message message--${message.role}`}
          key={message.id}
        >
          <div className="message-avatar" aria-hidden="true">
            {message.role === "assistant" ? (
              <Bot size={17} />
            ) : (
              <UserRound size={17} />
            )}
          </div>
          <div className="message-body">
            <div className="message-meta">
              <strong>{message.role === "assistant" ? "Assistant" : "You"}</strong>
              {message.status === "streaming" ? (
                <span className="message-state message-state--streaming">
                  Generating
                </span>
              ) : null}
              {message.status === "stopped" ? (
                <span className="message-state">
                  <CircleStop size={12} aria-hidden="true" /> Stopped
                </span>
              ) : null}
              {message.status === "error" ? (
                <span className="message-state message-state--error">Failed</span>
              ) : null}
            </div>
            {message.content ? (
              <p>{message.content}</p>
            ) : message.status === "streaming" ? (
              <span className="typing-indicator" aria-label="Generating response">
                <i />
                <i />
                <i />
              </span>
            ) : (
              <p className="empty-response">No response content received.</p>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}
