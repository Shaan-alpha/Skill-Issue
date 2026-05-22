import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const captureMock = vi.fn();

vi.mock("../posthog", () => ({
  track: captureMock,
  initPostHog: vi.fn(),
  identifyPostHog: vi.fn(),
}));

describe("typed event helpers", () => {
  beforeEach(() => {
    captureMock.mockClear();
  });

  afterEach(() => {
    vi.resetModules();
  });

  it("trackAnalyzeSubmitted emits the right event name + shape", async () => {
    const { trackAnalyzeSubmitted } = await import("../events");
    trackAnalyzeSubmitted({ tier: "Senior", score: 78, badge_count: 3 });
    expect(captureMock).toHaveBeenCalledWith("analyze_submitted", {
      tier: "Senior",
      score: 78,
      badge_count: 3,
    });
  });

  it("trackShareToggled emits the right event name + shape", async () => {
    const { trackShareToggled } = await import("../events");
    trackShareToggled({ now: "public" });
    expect(captureMock).toHaveBeenCalledWith("share_toggled", { now: "public" });
  });

  it("trackShareCardCopied emits each method correctly", async () => {
    const { trackShareCardCopied } = await import("../events");
    trackShareCardCopied({ method: "url" });
    trackShareCardCopied({ method: "png_clipboard" });
    trackShareCardCopied({ method: "png_download" });
    expect(captureMock).toHaveBeenNthCalledWith(1, "share_card_copied", { method: "url" });
    expect(captureMock).toHaveBeenNthCalledWith(2, "share_card_copied", { method: "png_clipboard" });
    expect(captureMock).toHaveBeenNthCalledWith(3, "share_card_copied", { method: "png_download" });
  });

  it("trackModeToggled emits from/to", async () => {
    const { trackModeToggled } = await import("../events");
    trackModeToggled({ from: "roast", to: "mentor" });
    expect(captureMock).toHaveBeenCalledWith("mode_toggled", { from: "roast", to: "mentor" });
  });

  it("trackSignInClicked emits no payload", async () => {
    const { trackSignInClicked } = await import("../events");
    trackSignInClicked();
    expect(captureMock).toHaveBeenCalledWith("sign_in_clicked", {});
  });
});
