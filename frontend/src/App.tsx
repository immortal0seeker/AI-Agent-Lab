import { useState } from "react";

import ChatPage from "./pages/ChatPage";
import AgentPage from "./pages/AgentPage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
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

  if (workspace === "agent") {
    return <AgentPage onSelectWorkspace={selectWorkspace} />;
  }
  if (workspace === "knowledge") {
    return <KnowledgeBasePage onSelectWorkspace={selectWorkspace} />;
  }
  return <ChatPage onSelectWorkspace={selectWorkspace} />;
}
