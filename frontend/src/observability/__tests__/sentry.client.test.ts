import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const initSpy = vi.fn();
const replaySentinel = { name: "Replay" };

vi.mock("@sentry/nextjs", () => ({
  init: (options: unknown) => initSpy(options),
  replayIntegration: () => replaySentinel,
}));

type InitOptions = {
  tracesSampleRate: number;
  replaysSessionSampleRate: number;
  replaysOnErrorSampleRate: number;
  integrations: unknown[];
};

function lastInitOptions(): InitOptions {
  expect(initSpy).toHaveBeenCalledTimes(1);
  return initSpy.mock.calls[0][0] as InitOptions;
}

describe("sentry.client init", () => {
  beforeEach(() => {
    vi.resetModules();
    initSpy.mockClear();
    vi.stubEnv("NEXT_PUBLIC_SENTRY_DSN", "https://key@o1.ingest.sentry.io/1");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("enables session replay with masking-safe defaults", async () => {
    await import("../sentry.client");
    const options = lastInitOptions();
    expect(options.integrations).toContain(replaySentinel);
    expect(options.replaysOnErrorSampleRate).toBe(1.0);
    expect(options.replaysSessionSampleRate).toBe(0.1);
    expect(options.tracesSampleRate).toBe(0.2);
  });

  it("reads sample rates from NEXT_PUBLIC_ env vars", async () => {
    vi.stubEnv("NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE", "0.5");
    vi.stubEnv("NEXT_PUBLIC_SENTRY_REPLAYS_SESSION_SAMPLE_RATE", "0.25");
    vi.stubEnv("NEXT_PUBLIC_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE", "0.75");
    await import("../sentry.client");
    const options = lastInitOptions();
    expect(options.tracesSampleRate).toBe(0.5);
    expect(options.replaysSessionSampleRate).toBe(0.25);
    expect(options.replaysOnErrorSampleRate).toBe(0.75);
  });

  it("does not init when the DSN is unset", async () => {
    vi.stubEnv("NEXT_PUBLIC_SENTRY_DSN", "");
    await import("../sentry.client");
    expect(initSpy).not.toHaveBeenCalled();
  });

  it("treats blank env vars as unset instead of sampling at 0", async () => {
    vi.stubEnv("NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE", "");
    vi.stubEnv("NEXT_PUBLIC_SENTRY_REPLAYS_SESSION_SAMPLE_RATE", "");
    vi.stubEnv("NEXT_PUBLIC_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE", "");
    await import("../sentry.client");
    const options = lastInitOptions();
    expect(options.tracesSampleRate).toBe(0.2);
    expect(options.replaysSessionSampleRate).toBe(0.1);
    expect(options.replaysOnErrorSampleRate).toBe(1.0);
  });

  it("honors an explicit zero", async () => {
    vi.stubEnv("NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE", "0");
    await import("../sentry.client");
    expect(lastInitOptions().tracesSampleRate).toBe(0);
  });
});
