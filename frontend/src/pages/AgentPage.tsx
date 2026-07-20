import { Circle } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  AgentApiError,
  createAgentRun,
  fetchAgentRun,
  fetchAgentToolCalls,
} from "../api/agent";
import { fetchHealth } from "../api/health";
import { fetchModels } from "../api/models";
import AgentRunPanel, {
  type AgentRunViewState,
} from "../components/agent/AgentRunPanel";
import AgentTaskForm from "../components/agent/AgentTaskForm";
import WorkspaceSidebar, {
  type ApiHealth,
} from "../components/WorkspaceSidebar";
import type { ModelOption } from "../types/models";
import {
  buildAgentRunUrl,
  readAgentRunId,
  type WorkspaceView,
} from "../utils/agentUrl";
import {
  clearStoredAgentRunId,
  readStoredAgentRunId,
  storeAgentRunId,
} from "../utils/agentRunStorage";

type ModelState =
  | { status: "loading" }
  | { status: "ready"; models: ModelOption[] }
  | { status: "error"; message: string };

type AgentPageError = {
  message: string;
  requestId: string | null;
};

type AgentPageProps = {
  onSelectWorkspace: (workspace: WorkspaceView) => void;
};

export function toolsCapableModels(models: ModelOption[]): ModelOption[] {
  return models.filter((model) => model.supports_tools);
}

export function toAgentPageError(error: unknown): AgentPageError {
  if (error instanceof AgentApiError) {
    return { message: error.message, requestId: error.requestId };
  }
  if (error instanceof Error) {
    return { message: error.message, requestId: null };
  }
  return { message: "Agent request failed", requestId: null };
}

export function createAgentRequestGate() {
  let currentRequest = 0;

  return {
    begin() {
      currentRequest += 1;
      return currentRequest;
    },
    invalidate() {
      currentRequest += 1;
    },
    isCurrent(request: number) {
      return request === currentRequest;
    },
  };
}

export default function AgentPage({ onSelectWorkspace }: AgentPageProps) {
  const requestGateRef = useRef<ReturnType<typeof createAgentRequestGate> | null>(
    null,
  );
  if (requestGateRef.current === null) {
    requestGateRef.current = createAgentRequestGate();
  }
  const requestGate = requestGateRef.current;
  const [health, setHealth] = useState<ApiHealth>({ status: "checking" });
  const [modelState, setModelState] = useState<ModelState>({
    status: "loading",
  });
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [taskInput, setTaskInput] = useState("");
  const initialRunId = useMemo(() => {
    const urlRunId = readAgentRunId(window.location.search);
    return urlRunId ?? readStoredAgentRunId(window.sessionStorage);
  }, []);
  const [runState, setRunState] = useState<AgentRunViewState>(() =>
    initialRunId === null
      ? { status: "empty" }
      : { status: "loading", message: "Loading Agent run..." },
  );

  useEffect(
    () => () => {
      requestGate.invalidate();
    },
    [requestGate],
  );

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
            message:
              error instanceof Error
                ? error.message
                : "Unable to reach backend health endpoint",
          });
        }
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  useEffect(() => {
    let isCurrent = true;
    fetchModels()
      .then((models) => {
        if (!isCurrent) {
          return;
        }
        const availableModels = toolsCapableModels(models);
        setModelState({ status: "ready", models: availableModels });
        setSelectedProvider(availableModels[0]?.provider ?? null);
        setSelectedModel(availableModels[0]?.model ?? null);
      })
      .catch((error: unknown) => {
        if (isCurrent) {
          setModelState({
            status: "error",
            message:
              error instanceof Error
                ? error.message
                : "Unable to load tools-capable models",
          });
        }
      });
    return () => {
      isCurrent = false;
    };
  }, []);

  useEffect(() => {
    if (initialRunId === null) {
      return;
    }
    let isCurrent = true;
    Promise.all([
      fetchAgentRun(initialRunId),
      fetchAgentToolCalls(initialRunId),
    ])
      .then(([run, toolCalls]) => {
        if (isCurrent) {
          setRunState({
            status: "result",
            run: { ...run, tool_calls: toolCalls },
          });
        }
      })
      .catch((error: unknown) => {
        if (isCurrent) {
          setRunState({ status: "error", ...toAgentPageError(error) });
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [initialRunId]);

  const availableModels =
    modelState.status === "ready" ? modelState.models : [];
  const disabledReason =
    modelState.status === "loading"
      ? "Loading tools-capable models..."
      : modelState.status === "error"
        ? modelState.message
        : availableModels.length === 0
          ? "No tools-capable model is configured"
          : null;
  const busy = runState.status === "loading";
  const visibleRunState: AgentRunViewState =
    runState.status !== "empty"
      ? runState
      : modelState.status === "loading"
        ? { status: "loading", message: "Loading Agent workspace..." }
        : modelState.status === "error"
          ? {
              status: "error",
              message: modelState.message,
              requestId: null,
            }
          : availableModels.length === 0
            ? { status: "no-models" }
            : runState;

  const submitTask = async () => {
    const input = taskInput.trim();
    if (
      !input ||
      selectedProvider === null ||
      selectedModel === null ||
      busy ||
      disabledReason !== null
    ) {
      return;
    }
    const request = requestGate.begin();
    setRunState({ status: "loading", message: "Running Agent task..." });
    try {
      const run = await createAgentRun({
        provider: selectedProvider,
        model: selectedModel,
        input,
      });
      storeAgentRunId(window.sessionStorage, run.id);
      if (!requestGate.isCurrent(request)) {
        return;
      }
      setRunState({ status: "result", run });
      window.history.replaceState(
        null,
        "",
        buildAgentRunUrl(window.location.href, run.id),
      );
    } catch (error: unknown) {
      if (!requestGate.isCurrent(request)) {
        return;
      }
      setRunState({ status: "error", ...toAgentPageError(error) });
    }
  };

  const newTask = () => {
    requestGate.invalidate();
    clearStoredAgentRunId(window.sessionStorage);
    setTaskInput("");
    setRunState({ status: "empty" });
    window.history.replaceState(
      null,
      "",
      buildAgentRunUrl(window.location.href, null),
    );
  };

  return (
    <main className="workspace-shell">
      <WorkspaceSidebar
        activeWorkspace="agent"
        health={health}
        onSelectWorkspace={onSelectWorkspace}
      />
      <section className="agent-workspace">
        <header className="agent-header">
          <div>
            <h1>Agent</h1>
            <p>Read-only ToolCall workspace</p>
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
        <div className="agent-content">
          <div className="agent-content-inner">
            <AgentTaskForm
              models={availableModels}
              provider={selectedProvider}
              model={selectedModel}
              input={taskInput}
              busy={busy}
              disabledReason={disabledReason}
              hasRun={runState.status === "result" || runState.status === "error"}
              onSelectModel={(provider, model) => {
                setSelectedProvider(provider);
                setSelectedModel(model);
              }}
              onInputChange={setTaskInput}
              onSubmit={() => void submitTask()}
              onNewTask={newTask}
            />
            <AgentRunPanel state={visibleRunState} />
          </div>
        </div>
      </section>
    </main>
  );
}
