import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TraceApiError } from "../api/traces";
import TraceTimelinePage, {
  createTraceRequestGate,
  toTracePageError,
} from "./TraceTimelinePage";


afterEach(() => {
  vi.unstubAllGlobals();
});


describe("TraceTimelinePage", () => {
  it("renders the independent list and detail loading shell", () => {
    vi.stubGlobal("window", {
      location: {
        search: "?workspace=trace",
        href: "http://localhost:5173/?workspace=trace",
      },
      history: { replaceState: vi.fn() },
    });
    const html = renderToStaticMarkup(
      <TraceTimelinePage onSelectWorkspace={vi.fn()} />,
    );

    expect(html).toContain("Trace Timeline workspace");
    expect(html).toContain("Loading recent Trace Runs...");
  });

  it("normalizes structured and unknown errors", () => {
    expect(
      toTracePageError(
        new TraceApiError("Trace run not found", {
          requestId: "request-trace-1",
        }),
      ),
    ).toEqual({ message: "Trace run not found", requestId: "request-trace-1" });
    expect(toTracePageError("unknown")).toEqual({
      message: "Trace request failed",
      requestId: null,
    });
  });

  it("invalidates stale request generations", () => {
    const gate = createTraceRequestGate();
    const first = gate.begin();
    const second = gate.begin();

    expect(gate.isCurrent(first)).toBe(false);
    expect(gate.isCurrent(second)).toBe(true);
    gate.invalidate();
    expect(gate.isCurrent(second)).toBe(false);
  });
});
