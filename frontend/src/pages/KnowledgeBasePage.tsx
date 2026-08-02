import { Circle, Database } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { fetchHealth } from "../api/health";
import {
  createKnowledgeBase,
  fetchKnowledgeBases,
  uploadKnowledgeDocument,
} from "../api/knowledge";
import DocumentStatusCard from "../components/knowledge/DocumentStatusCard";
import FileUploadPanel from "../components/knowledge/FileUploadPanel";
import KnowledgeBaseCreateForm from "../components/knowledge/KnowledgeBaseCreateForm";
import KnowledgeBaseList, {
  type KnowledgeBaseListState,
} from "../components/knowledge/KnowledgeBaseList";
import WorkspaceSidebar, {
  type ApiHealth,
} from "../components/WorkspaceSidebar";
import type {
  KnowledgeBase,
  KnowledgeDocument,
} from "../types/knowledge";
import type { WorkspaceView } from "../utils/agentUrl";

type KnowledgeBasePageProps = {
  onSelectWorkspace: (workspace: WorkspaceView) => void;
};

type UploadState =
  | { status: "idle" }
  | { status: "uploading" }
  | { status: "error"; message: string }
  | { status: "result"; document: KnowledgeDocument };

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export default function KnowledgeBasePage({
  onSelectWorkspace,
}: KnowledgeBasePageProps) {
  const mountedRef = useRef(true);
  const listRequestRef = useRef(0);
  const createRequestRef = useRef(0);
  const uploadRequestRef = useRef(0);
  const selectedIdRef = useRef<string | null>(null);
  const [health, setHealth] = useState<ApiHealth>({ status: "checking" });
  const [listState, setListState] = useState<KnowledgeBaseListState>({
    status: "loading",
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [uploadState, setUploadState] = useState<UploadState>({
    status: "idle",
  });

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      listRequestRef.current += 1;
      createRequestRef.current += 1;
      uploadRequestRef.current += 1;
    };
  }, []);

  useEffect(() => {
    let isCurrent = true;
    fetchHealth()
      .then((data) => {
        if (isCurrent) {
          setHealth({ status: "healthy", service: data.service });
        }
      })
      .catch((error: unknown) => {
        if (isCurrent) {
          setHealth({
            status: "error",
            message: errorMessage(
              error,
              "Unable to reach backend health endpoint",
            ),
          });
        }
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  const loadKnowledgeBases = useCallback(async () => {
    const request = ++listRequestRef.current;
    setListState({ status: "loading" });
    try {
      const items = await fetchKnowledgeBases();
      if (!mountedRef.current || request !== listRequestRef.current) {
        return;
      }
      setListState({ status: "ready", items });
      setSelectedId((current) => {
        const next =
          current !== null && items.some((item) => item.id === current)
            ? current
            : (items[0]?.id ?? null);
        selectedIdRef.current = next;
        return next;
      });
    } catch (error: unknown) {
      if (!mountedRef.current || request !== listRequestRef.current) {
        return;
      }
      setListState({
        status: "error",
        message: errorMessage(error, "Unable to load Knowledge Bases"),
      });
    }
  }, []);

  useEffect(() => {
    void loadKnowledgeBases();
  }, [loadKnowledgeBases]);

  const items = listState.status === "ready" ? listState.items : [];
  const selectedKnowledgeBase = useMemo<KnowledgeBase | null>(
    () => items.find((item) => item.id === selectedId) ?? null,
    [items, selectedId],
  );

  const submitCreate = async () => {
    const trimmedName = name.trim();
    if (!trimmedName || creating || listState.status === "loading") {
      return;
    }
    const request = ++createRequestRef.current;
    setCreating(true);
    setCreateError(null);
    try {
      const trimmedDescription = description.trim();
      const created = await createKnowledgeBase({
        name: trimmedName,
        description: trimmedDescription || null,
      });
      if (!mountedRef.current || request !== createRequestRef.current) {
        return;
      }
      setListState((current) => ({
        status: "ready",
        items: [
          created,
          ...(current.status === "ready"
            ? current.items.filter((item) => item.id !== created.id)
            : []),
        ],
      }));
      setSelectedId(created.id);
      selectedIdRef.current = created.id;
      uploadRequestRef.current += 1;
      setUploadState({ status: "idle" });
      setName("");
      setDescription("");
    } catch (error: unknown) {
      if (!mountedRef.current || request !== createRequestRef.current) {
        return;
      }
      setCreateError(
        errorMessage(error, "Unable to create Knowledge Base"),
      );
    } finally {
      if (mountedRef.current && request === createRequestRef.current) {
        setCreating(false);
      }
    }
  };

  const uploading = uploadState.status === "uploading";

  const selectKnowledgeBase = (knowledgeBaseId: string) => {
    if (uploading) {
      return;
    }
    selectedIdRef.current = knowledgeBaseId;
    setSelectedId(knowledgeBaseId);
    uploadRequestRef.current += 1;
    setUploadState({ status: "idle" });
  };

  const submitUpload = async (file: File): Promise<boolean> => {
    const knowledgeBaseId = selectedIdRef.current;
    if (knowledgeBaseId === null || uploading || creating) {
      return false;
    }
    const request = ++uploadRequestRef.current;
    setUploadState({ status: "uploading" });
    try {
      const document = await uploadKnowledgeDocument(knowledgeBaseId, file);
      if (
        !mountedRef.current ||
        request !== uploadRequestRef.current ||
        selectedIdRef.current !== knowledgeBaseId
      ) {
        return false;
      }
      if (document.knowledge_base_id !== knowledgeBaseId) {
        setUploadState({
          status: "error",
          message:
            "Knowledge API returned a document for a different Knowledge Base",
        });
        return false;
      }
      setUploadState({ status: "result", document });
      return true;
    } catch (error: unknown) {
      if (
        !mountedRef.current ||
        request !== uploadRequestRef.current ||
        selectedIdRef.current !== knowledgeBaseId
      ) {
        return false;
      }
      setUploadState({
        status: "error",
        message: errorMessage(error, "Unable to upload document"),
      });
      return false;
    }
  };

  return (
    <main className="workspace-shell">
      <WorkspaceSidebar
        activeWorkspace="knowledge"
        health={health}
        onSelectWorkspace={onSelectWorkspace}
      />
      <section className="knowledge-workspace">
        <header className="knowledge-header">
          <div>
            <h1>Knowledge</h1>
            <p>Knowledge Base workspace</p>
          </div>
          <span className={`agent-header-status agent-header-status--${health.status}`}>
            <Circle size={9} fill="currentColor" aria-hidden="true" />
            {health.status === "healthy"
              ? "API connected"
              : health.status === "error"
                ? "API unavailable"
                : "Checking API"}
          </span>
        </header>
        <div className="knowledge-content">
          <div className="knowledge-library-column">
            <KnowledgeBaseCreateForm
              name={name}
              description={description}
              busy={creating}
              disabled={uploading || listState.status === "loading"}
              error={createError}
              onNameChange={(value) => {
                setName(value);
                setCreateError(null);
              }}
              onDescriptionChange={(value) => {
                setDescription(value);
                setCreateError(null);
              }}
              onSubmit={() => void submitCreate()}
            />
            <KnowledgeBaseList
              state={listState}
              selectedId={selectedId}
              disabled={creating || uploading}
              onSelect={selectKnowledgeBase}
              onRetry={() => void loadKnowledgeBases()}
            />
          </div>
          <section className="knowledge-detail-panel" aria-live="polite">
            {selectedKnowledgeBase === null ? (
              <div className="knowledge-detail-empty">
                <Database size={24} aria-hidden="true" />
                <strong>Select a Knowledge Base</strong>
                <span>Create or select a Knowledge Base to ingest a document.</span>
              </div>
            ) : (
              <div className="knowledge-selected-summary">
                <span className="knowledge-eyebrow">Selected Knowledge Base</span>
                <h2>{selectedKnowledgeBase.name}</h2>
                <p>{selectedKnowledgeBase.description ?? "No description"}</p>
                <dl>
                  <div>
                    <dt>Knowledge Base ID</dt>
                    <dd>{selectedKnowledgeBase.id}</dd>
                  </div>
                  <div>
                    <dt>Vector Store</dt>
                    <dd>{selectedKnowledgeBase.vector_store}</dd>
                  </div>
                </dl>
                <FileUploadPanel
                  key={selectedKnowledgeBase.id}
                  busy={uploading}
                  disabled={creating}
                  error={
                    uploadState.status === "error"
                      ? uploadState.message
                      : null
                  }
                  onFileChange={() => {
                    if (uploadState.status === "error") {
                      setUploadState({ status: "idle" });
                    }
                  }}
                  onUpload={submitUpload}
                />
                {uploadState.status === "result" ? (
                  <DocumentStatusCard document={uploadState.document} />
                ) : null}
              </div>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}
