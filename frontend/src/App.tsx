import { useState } from "react";

import ChatPage from "./pages/ChatPage";
import AgentPage from "./pages/AgentPage";
import {
  buildWorkspaceUrl,
  readWorkspace,
  type WorkspaceView,
} from "./utils/agentUrl";

export default function App() {
  const [workspace, setWorkspace] = useState<WorkspaceView>(() =>
    readWorkspace(window.location.search),
  );
  const selectWorkspace = (nextWorkspace: WorkspaceView) => {
    setWorkspace(nextWorkspace);
    window.history.replaceState(
      null,
      "",
      buildWorkspaceUrl(window.location.href, nextWorkspace),
    );
  };

  return workspace === "agent" ? (
    <AgentPage onSelectWorkspace={selectWorkspace} />
  ) : (
    <ChatPage onSelectWorkspace={selectWorkspace} />
  );
}
