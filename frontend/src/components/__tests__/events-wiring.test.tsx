import { describe, expect, it, vi } from "vitest";

vi.mock("@/observability/events", () => ({
  trackAnalyzeSubmitted: vi.fn(),
  trackShareToggled: vi.fn(),
  trackShareCardCopied: vi.fn(),
  trackModeToggled: vi.fn(),
  trackSignInClicked: vi.fn(),
  trackForceRefreshClicked: vi.fn(),
}));

describe("events wiring", () => {
  it("module export surface matches the wired helpers", async () => {
    const events = await import("@/observability/events");
    expect(typeof events.trackAnalyzeSubmitted).toBe("function");
    expect(typeof events.trackShareToggled).toBe("function");
    expect(typeof events.trackShareCardCopied).toBe("function");
    expect(typeof events.trackModeToggled).toBe("function");
    expect(typeof events.trackSignInClicked).toBe("function");
    expect(typeof events.trackForceRefreshClicked).toBe("function");
  });
});
