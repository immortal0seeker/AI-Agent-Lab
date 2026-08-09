const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export type WorkspaceView = "chat" | "agent" | "knowledge" | "trace";

export function readWorkspace(search: string): WorkspaceView {
  const workspace = new URLSearchParams(search).get("workspace");
  return workspace === "agent" ||
    workspace === "knowledge" ||
    workspace === "trace"
    ? workspace
    : "chat";
}

export function readAgentRunId(search: string): string | null {
  const runId = new URLSearchParams(search).get("run");
  return runId !== null && UUID_PATTERN.test(runId) ? runId : null;
}

export function readTraceRunId(search: string): string | null {
  const runId = new URLSearchParams(search).get("run");
  return runId !== null && UUID_PATTERN.test(runId) ? runId : null;
}

export function buildWorkspaceUrl(
  href: string,
  workspace: WorkspaceView,
): string {
  const url = new URL(href);
  const currentWorkspace = readWorkspace(url.search);
  if (currentWorkspace !== workspace) {
    url.searchParams.delete("run");
  }
  if (workspace === "chat") {
    url.searchParams.delete("workspace");
  } else {
    url.searchParams.set("workspace", workspace);
  }
  return url.toString();
}

export function buildTraceRunUrl(
  href: string,
  runId: string | null,
): string {
  const url = new URL(href);
  if (runId === null) {
    url.searchParams.delete("run");
  } else {
    url.searchParams.set("run", runId);
  }
  return url.toString();
}

export function buildAgentRunUrl(
  href: string,
  runId: string | null,
): string {
  const url = new URL(href);
  if (runId === null) {
    url.searchParams.delete("run");
  } else {
    url.searchParams.set("run", runId);
  }
  return url.toString();
}
