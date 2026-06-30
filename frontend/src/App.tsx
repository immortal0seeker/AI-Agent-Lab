import { API_BASE_URL } from "./api/client";

export default function App() {
  return (
    <main className="workspace-shell">
      <section className="workspace-panel">
        <p className="eyebrow">Plan 1 / Milestone 1</p>
        <h1>AI Agent Lab</h1>
        <p>
          Project foundation is being assembled. The frontend is ready to use
          the backend API base URL below.
        </p>
        <code>{API_BASE_URL}</code>
      </section>
    </main>
  );
}
