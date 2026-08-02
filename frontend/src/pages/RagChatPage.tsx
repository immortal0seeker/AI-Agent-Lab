import { AlertCircle, LoaderCircle, MessageSquarePlus } from "lucide-react";
import { useEffect } from "react";

import ModelSelector from "../components/ModelSelector";
import RagAnswerPanel from "../components/rag/RagAnswerPanel";
import RagComposer from "../components/rag/RagComposer";
import {
  type RagStoreHook,
  useRagStore,
} from "../stores/ragStore";
import type { KnowledgeBase } from "../types/knowledge";
import type { RagTurn } from "../types/rag";

type RagChatPageProps = {
  knowledgeBase: KnowledgeBase;
  ragStore?: RagStoreHook;
};

export function selectRagOwnerView(
  selectedKnowledgeBaseId: string | null,
  visibleKnowledgeBaseId: string,
  turns: RagTurn[],
): { ownerCurrent: boolean; turns: RagTurn[] } {
  const ownerCurrent = selectedKnowledgeBaseId === visibleKnowledgeBaseId;
  return { ownerCurrent, turns: ownerCurrent ? turns : [] };
}

export default function RagChatPage({
  knowledgeBase,
  ragStore,
}: RagChatPageProps) {
  const store = ragStore ?? useRagStore;
  const models = store((state) => state.models);
  const selectedProvider = store((state) => state.selectedProvider);
  const selectedModel = store((state) => state.selectedModel);
  const selectedKnowledgeBaseId = store(
    (state) => state.selectedKnowledgeBaseId,
  );
  const conversationId = store((state) => state.conversationId);
  const turns = store((state) => state.turns);
  const workspaceStatus = store((state) => state.workspaceStatus);
  const requestStatus = store((state) => state.requestStatus);
  const workspaceError = store((state) => state.workspaceError);
  const requestError = store((state) => state.requestError);
  const initialize = store((state) => state.initialize);
  const setKnowledgeBase = store((state) => state.setKnowledgeBase);
  const selectModel = store((state) => state.selectModel);
  const sendQuery = store((state) => state.sendQuery);
  const newChat = store((state) => state.newChat);

  useEffect(() => {
    setKnowledgeBase(knowledgeBase.id, knowledgeBase.name);
  }, [knowledgeBase.id, knowledgeBase.name, setKnowledgeBase]);

  useEffect(() => {
    void initialize();
  }, [initialize]);

  const busy = requestStatus === "sending";
  const noModel =
    workspaceStatus === "ready" &&
    (selectedProvider === null || selectedModel === null);
  const ownerView = selectRagOwnerView(
    selectedKnowledgeBaseId,
    knowledgeBase.id,
    turns,
  );

  return (
    <section className="rag-chat-page" aria-labelledby="rag-chat-heading">
      <header className="rag-chat-header">
        <div>
          <span className="knowledge-eyebrow">Grounded answers</span>
          <h3 id="rag-chat-heading">Ask {knowledgeBase.name}</h3>
          <p>Ask a question using only sources from this Knowledge Base.</p>
        </div>
        <button
          type="button"
          disabled={busy || !ownerView.ownerCurrent}
          onClick={newChat}
        >
          <MessageSquarePlus size={15} aria-hidden="true" />
          New RAG chat
        </button>
      </header>

      {workspaceStatus === "loading" || workspaceStatus === "idle" ? (
        <div className="rag-workspace-state" role="status">
          <LoaderCircle size={18} aria-hidden="true" />
          Loading RAG models...
        </div>
      ) : workspaceStatus === "error" ? (
        <div className="rag-workspace-state rag-workspace-state--error" role="alert">
          <AlertCircle size={18} aria-hidden="true" />
          <span>{workspaceError ?? "Unable to initialize RAG workspace"}</span>
          <button type="button" onClick={() => void initialize()}>
            Retry
          </button>
        </div>
      ) : (
        <>
          <div className="rag-chat-toolbar">
            <ModelSelector
              models={models}
              provider={selectedProvider}
              model={selectedModel}
              disabled={busy || !ownerView.ownerCurrent}
              onChange={selectModel}
            />
            {!ownerView.ownerCurrent ? (
              <span>Synchronizing Knowledge Base...</span>
            ) : conversationId ? (
              <code aria-label="RAG Conversation ID">{conversationId}</code>
            ) : (
              <span>Conversation starts with the first question</span>
            )}
          </div>

          {!ownerView.ownerCurrent ? (
            <div className="rag-workspace-state" role="status">
              Preparing the selected Knowledge Base...
            </div>
          ) : noModel ? (
            <div className="rag-workspace-state">
              <strong>No models configured for RAG Chat</strong>
              <span>Add a model to the Registry before asking a question.</span>
            </div>
          ) : ownerView.turns.length === 0 ? (
            <div className="rag-chat-empty">
              <strong>Ask a question to start a grounded conversation</strong>
              <span>Answers use the selected Knowledge Base and show their sources.</span>
            </div>
          ) : (
            <div className="rag-turn-list" aria-live="polite">
              {ownerView.turns.map((turn) => (
                <RagAnswerPanel key={turn.rag_query_id} turn={turn} />
              ))}
            </div>
          )}

          <RagComposer
            busy={busy}
            disabled={noModel || !ownerView.ownerCurrent}
            error={requestError}
            onSend={sendQuery}
          />
        </>
      )}
    </section>
  );
}
