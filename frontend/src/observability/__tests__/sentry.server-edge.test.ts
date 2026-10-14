import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { APP_VERSION } from "@/lib/site";

const initSpy = vi.fn();

vi.mock("@sentry/nextjs", () => ({
  init: (options: unknown) => initSpy(options),
  httpIntegration: (options: unknown) => ({ name: "Http", options }),
}));

type InitOptions = {
  release?: string;
  beforeSend?: (event: Record<string, unknown>) => Record<string, unknown>;
  integrations?: unknown[];
  dataCollection?: unknown;
  beforeSendTransaction?: unknown;
  sendDefaultPii?: unknown;
};

function lastInitOptions(): InitOptions {
  expect(initSpy).toHaveBeenCalledTimes(1);
  return initSpy.mock.calls[0][0] as InitOptions;
}

// Server and edge events carried no release while the browser's and the
// backend's did, so a server-side error couldn't be tied to a deploy.
describe.each([
  ["server", () => import("../sentry.server")],
  ["edge", () => import("../sentry.edge")],
])("sentry.%s init", (_name, load) => {
  beforeEach(() => {
    vi.resetModules();
    initSpy.mockClear();
    vi.stubEnv("SENTRY_DSN", "https://key@o1.ingest.sentry.io/1");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("tags events with the app release", async () => {
    await load();
    expect(lastInitOptions().release).toBe(APP_VERSION);
  });

  it("scrubs cookies and auth headers before sending", async () => {
    await load();
    const { beforeSend } = lastInitOptions();
    const event = beforeSend!({
      request: { headers: { cookie: "si_session=secret", authorization: "Bearer x", accept: "*/*" } },
    }) as { request: { headers: Record<string, string> } };
    expect(event.request.headers).toEqual({ accept: "*/*" });
  });

  it("collects no PII at the source and scrubs errors and transactions alike", async () => {
    const { SENTRY_DATA_COLLECTION, scrubEvent } = await import("../scrub");
    await load();
    const options = lastInitOptions();
    expect(options).not.toHaveProperty("sendDefaultPii");
    expect(options.dataCollection).toBe(SENTRY_DATA_COLLECTION);
    expect(options.beforeSend).toBe(scrubEvent);
    expect(options.beforeSendTransaction).toBe(scrubEvent);
  });
});

describe("sentry.server request bodies", () => {
  beforeEach(() => {
    vi.resetModules();
    initSpy.mockClear();
    vi.stubEnv("SENTRY_DSN", "https://key@o1.ingest.sentry.io/1");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  // In 10.x the Node server captures incoming bodies whatever httpBodies
  // says; replacing the default Http integration by name turns that off.
  it("captures no incoming request bodies", async () => {
    await import("../sentry.server");
    expect(lastInitOptions().integrations).toContainEqual({
      name: "Http",
      options: { disableIncomingRequestSpans: true, maxIncomingRequestBodySize: "none" },
    });
  });
});
