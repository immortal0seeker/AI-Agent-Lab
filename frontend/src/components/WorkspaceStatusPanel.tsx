import { AlertCircle, LoaderCircle, RotateCcw } from "lucide-react";

type WorkspaceStatusPanelProps =
  | { status: "loading" }
  | { status: "error"; message: string; onRetry: () => void };

export default function WorkspaceStatusPanel(
  props: WorkspaceStatusPanelProps,
) {
  if (props.status === "loading") {
    return (
      <div className="workspace-state" role="status" aria-live="polite">
        <LoaderCircle size={20} aria-hidden="true" />
        <strong>Loading Chat workspace...</strong>
        <span>Loading models and recent conversations.</span>
      </div>
    );
  }

  return (
    <div className="workspace-state workspace-state--error" role="alert">
      <AlertCircle size={22} aria-hidden="true" />
      <strong>Unable to load Chat workspace</strong>
      <span>{props.message}</span>
      <button type="button" onClick={props.onRetry}>
        <RotateCcw size={15} aria-hidden="true" />
        Retry
      </button>
    </div>
  );
}
