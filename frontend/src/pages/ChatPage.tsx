import { AlertCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchHealth } from "../api/health";
import ChatHeader from "../components/ChatHeader";
import MessageComposer from "../components/MessageComposer";
import MessageList from "../components/MessageList";
import WorkspaceSidebar, {
  type ApiHealth,
} from "../components/WorkspaceSidebar";
import {
  DEFAULT_MODEL,
  DEFAULT_PROVIDER,
  useChatStore,
} from "../stores/chatStore";

export default function ChatPage() {
  const [health, setHealth] = useState<ApiHealth>({ status: "checking" });
  const messages = useChatStore((state) => state.messages);
  const status = useChatStore((state) => state.status);
  const error = useChatStore((state) => state.error);
  const sendMessage = useChatStore((state) => state.sendMessage);
  const stopGeneration = useChatStore((state) => state.stopGeneration);
  const newChat = useChatStore((state) => state.newChat);

  useEffect(() => {
    let isCurrent = true;
    fetchHealth()
      .then((data) => {
        if (isCurrent) {
          setHealth({ status: "healthy", service: data.service });
        }
      })
      .catch((healthError: unknown) => {
        if (isCurrent) {
          setHealth({
            status: "error",
            message:
              healthError instanceof Error
                ? healthError.message
                : "Unable to reach backend health endpoint",
          });
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  return (
    <main className="workspace-shell">
      <WorkspaceSidebar health={health} onNewChat={newChat} />
      <section className="chat-workspace">
        <ChatHeader
          provider={DEFAULT_PROVIDER}
          model={DEFAULT_MODEL}
          isStreaming={status === "streaming"}
        />
        {error ? (
          <div className="error-banner" role="alert">
            <AlertCircle size={17} aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : null}
        <div className="chat-content">
          <MessageList messages={messages} />
        </div>
        <footer className="composer-region">
          <MessageComposer
            isStreaming={status === "streaming"}
            onSend={sendMessage}
            onStop={stopGeneration}
          />
          <p>Responses are persisted only after a completed stream.</p>
        </footer>
      </section>
    </main>
  );
}
