import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const captureMock = vi.fn();
const identifyMock = vi.fn();
const initMock = vi.fn();

vi.mock("posthog-js", () => ({
  default: {
    init: initMock,
    capture: captureMock,
    identify: identifyMock,
    __loaded: false,
  },
}));

describe("posthog adapter — fail-open behaviour", () => {
  beforeEach(() => {
    vi.resetModules();
    captureMock.mockClear();
    identifyMock.mockClear();
    initMock.mockClear();
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_POSTHOG_KEY;
  });

  it("does NOT call posthog.init when the API key env var is unset", async () => {
    delete process.env.NEXT_PUBLIC_POSTHOG_KEY;
    const { initPostHog } = await import("../posthog");
    initPostHog();
    expect(initMock).not.toHaveBeenCalled();
  });

  it("calls posthog.init with the configured key + host when env vars are set", async () => {
    process.env.NEXT_PUBLIC_POSTHOG_KEY = "phc_test";
    process.env.NEXT_PUBLIC_POSTHOG_HOST = "https://us.i.posthog.com";
    const { initPostHog } = await import("../posthog");
    initPostHog();
    expect(initMock).toHaveBeenCalledTimes(1);
    const [key, opts] = initMock.mock.calls[0];
    expect(key).toBe("phc_test");
    expect(opts.api_host).toBe("https://us.i.posthog.com");
  });

  it("track() is a no-op when posthog wasn't initialised", async () => {
    delete process.env.NEXT_PUBLIC_POSTHOG_KEY;
    const { track } = await import("../posthog");
    track("analyze_submitted", { score: 80, tier: "Senior", badge_count: 3 });
    expect(captureMock).not.toHaveBeenCalled();
  });
});
