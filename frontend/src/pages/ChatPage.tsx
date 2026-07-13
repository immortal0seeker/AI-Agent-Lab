import { AlertCircle, LoaderCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { fetchHealth } from "../api/health";
import ChatHeader from "../components/ChatHeader";
import MessageComposer from "../components/MessageComposer";
import MessageList from "../components/MessageList";
import WorkspaceStatusPanel from "../components/WorkspaceStatusPanel";
import WorkspaceSidebar, {
  type ApiHealth,
} from "../components/WorkspaceSidebar";
import { useChatStore } from "../stores/chatStore";
import {
  buildConversationUrl,
  readConversationId,
} from "../utils/conversationUrl";

export default function ChatPage() {
  const [health, setHealth] = useState<ApiHealth>({ status: "checking" });
  const messages = useChatStore((state) => state.messages);
  const models = useChatStore((state) => state.models);
  const conversations = useChatStore((state) => state.conversations);
  const conversationId = useChatStore((state) => state.conversationId);
  const selectedProvider = useChatStore((state) => state.selectedProvider);
  const selectedModel = useChatStore((state) => state.selectedModel);
  const status = useChatStore((state) => state.status);
  const workspaceStatus = useChatStore((state) => state.workspaceStatus);
  const conversationStatus = useChatStore((state) => state.conversationStatus);
  const error = useChatStore((state) => state.error);
  const workspaceError = useChatStore((state) => state.workspaceError);
  const initialize = useChatStore((state) => state.initialize);
  const selectModel = useChatStore((state) => state.selectModel);
  const selectConversation = useChatStore((state) => state.selectConversation);
  const sendMessage = useChatStore((state) => state.sendMessage);
  const stopGeneration = useChatStore((state) => state.stopGeneration);
  const newChat = useChatStore((state) => state.newChat);

  useEffect(() => {
    void initialize(readConversationId(window.location.search));
  }, [initialize]);

  useEffect(() => {
    if (workspaceStatus !== "ready") {
      return;
    }
    const nextUrl = buildConversationUrl(window.location.href, conversationId);
    window.history.replaceState(null, "", nextUrl);
  }, [conversationId, workspaceStatus]);

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

  const isStreaming = status === "streaming";
  const isConversationLoading = conversationStatus === "loading";
  const composerDisabled =
    workspaceStatus !== "ready" ||
    isConversationLoading ||
    selectedProvider === null ||
    selectedModel === null;
  const visibleError =
    workspaceStatus === "ready" ? (error ?? workspaceError) : null;
  const retryInitialization = () => {
    void initialize(readConversationId(window.location.search));
  };

  return (
    <main className="workspace-shell">
      <WorkspaceSidebar
        health={health}
        conversations={conversations}
        selectedConversationId={conversationId}
        conversationsLoading={workspaceStatus === "loading"}
        navigationDisabled={isStreaming || isConversationLoading}
        onNewChat={newChat}
        onSelectConversation={(id) => void selectConversation(id)}
      />
      <section className="chat-workspace">
        <ChatHeader
          models={models}
          provider={selectedProvider}
          model={selectedModel}
          workspaceStatus={workspaceStatus}
          isStreaming={isStreaming}
          modelSelectionDisabled={
            workspaceStatus !== "ready" || isStreaming || isConversationLoading
          }
          onSelectModel={selectModel}
        />
        {visibleError ? (
          <div className="error-banner" role="alert">
            <AlertCircle size={17} aria-hidden="true" />
            <span>{visibleError}</span>
          </div>
        ) : null}
        <div className="chat-content">
          {workspaceStatus === "error" ? (
            <WorkspaceStatusPanel
              status="error"
              message={
                workspaceError ?? "Unable to initialize Chat workspace"
              }
              onRetry={retryInitialization}
            />
          ) : workspaceStatus !== "ready" ? (
            <WorkspaceStatusPanel status="loading" />
          ) : (
            <>
              {isConversationLoading ? (
                <div className="conversation-loading" role="status">
                  <LoaderCircle size={15} aria-hidden="true" />
                  Loading conversation...
                </div>
              ) : null}
              <MessageList messages={messages} />
            </>
          )}
        </div>
        <footer className="composer-region">
          <MessageComposer
            isStreaming={isStreaming}
            disabled={composerDisabled}
            onSend={sendMessage}
            onStop={stopGeneration}
          />
          <p>Responses are persisted only after a completed stream.</p>
        </footer>
      </section>
    </main>
  );
}
