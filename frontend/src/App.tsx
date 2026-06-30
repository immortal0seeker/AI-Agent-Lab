import { useEffect, useState } from "react";

import { API_BASE_URL } from "./api/client";
import { fetchHealth, type HealthResponse } from "./api/health";

type HealthState =
  | { status: "checking" }
  | { status: "healthy"; data: HealthResponse }
  | { status: "error"; message: string };

export default function App() {
  const [health, setHealth] = useState<HealthState>({ status: "checking" });

  useEffect(() => {
    let isCurrent = true;

    setHealth({ status: "checking" });
    fetchHealth()
      .then((data) => {
        if (isCurrent) {
          setHealth({ status: "healthy", data });
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

  return (
    <main className="workspace-shell">
      <section className="workspace-panel">
        <p className="eyebrow">Plan 1 / Milestone 1</p>
        <h1>AI Agent Lab</h1>
        <p>
          Project foundation is being assembled. The frontend now checks the
          backend health endpoint below.
        </p>

        <div className={`health-card health-card--${health.status}`}>
          <div>
            <p className="health-label">Backend API</p>
            <code>{API_BASE_URL}</code>
          </div>

          {health.status === "checking" ? (
            <p className="health-status">Checking health...</p>
          ) : null}

          {health.status === "healthy" ? (
            <div className="health-result">
              <p className="health-status">Backend healthy</p>
              <p>
                Service <strong>{health.data.service}</strong> returned{" "}
                <strong>{health.data.status}</strong>.
              </p>
            </div>
          ) : null}

          {health.status === "error" ? (
            <div className="health-result">
              <p className="health-status">Backend error</p>
              <p>{health.message}</p>
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}
