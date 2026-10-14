import { describe, expect, it } from "vitest";
import type { Event } from "@sentry/nextjs";
import { httpHeadersToSpanAttributes, requestDataIntegration } from "@sentry/core";
import { FILTERED, SENTRY_DATA_COLLECTION, filterQuery, filterUrl, scrubEvent } from "./scrub";

const CANARIES = {
  session: "canary-session-7f3a",
  posthog: "canary-posthog-7f3a",
  internal: "canary-internal-7f3a",
  oidc: "canary-oidc-7f3a",
  ip: "203.0.113.77",
  city: "canary-city-7f3a",
  code: "canary-code-7f3a",
  state: "canary-state-7f3a",
  body: "canary-body-7f3a",
};

function leaks(value: unknown): string[] {
  const text = JSON.stringify(value);
  return Object.entries(CANARIES)
    .filter(([, canary]) => text.includes(canary))
    .map(([name]) => name);
}

function signedInHeaders(): Record<string, string> {
  return {
    "user-agent": "canary-agent",
    referer: `https://skillissue.tech/me?code=${CANARIES.code}`,
    cookie: `si_session=${CANARIES.session}; ph_phc_x_posthog=${CANARIES.posthog}`,
    "x-internal-secret": CANARIES.internal,
    "x-vercel-oidc-token": CANARIES.oidc,
    "x-vercel-forwarded-for": CANARIES.ip,
    "x-vercel-ip-city": CANARIES.city,
  };
}

describe("scrubEvent", () => {
  it("keeps only allow-listed request headers, with the referer's query filtered", () => {
    const event = scrubEvent({ request: { headers: signedInHeaders() } } as Event);
    expect(event.request?.headers).toEqual({
      "user-agent": "canary-agent",
      referer: `https://skillissue.tech/me?code=${FILTERED}`,
    });
  });

  it("matches header names in any case", () => {
    const event = scrubEvent({
      request: { headers: { "User-Agent": "ua", COOKIE: "s", Accept: "*/*" } },
    } as Event);
    expect(event.request?.headers).toEqual({ "User-Agent": "ua", Accept: "*/*" });
  });

  it("drops cookies, bodies, env and the visitor IP", () => {
    const event = scrubEvent({
      request: { cookies: { si_session: "s" }, data: CANARIES.body, env: { REMOTE_ADDR: CANARIES.ip } },
      user: { id: "u1", ip_address: CANARIES.ip, email: "x@example.com" },
    } as Event);
    expect(event.request).toEqual({});
    expect(event.user).toEqual({ id: "u1" });
  });

  it("filters sensitive query values in every query_string shape and in the URL", () => {
    const asString = scrubEvent({
      request: { query_string: "mode=roast&code=a&state=b", url: "https://x.test/u/a?code=a&mode=roast" },
    } as Event);
    const asObject = scrubEvent({ request: { query_string: { code: "a", mode: "roast" } } } as Event);
    const asPairs = scrubEvent({ request: { query_string: [["state", "a"], ["page", "2"]] } } as Event);
    expect(asString.request?.query_string).toBe(`mode=roast&code=${FILTERED}&state=${FILTERED}`);
    expect(asString.request?.url).toBe(`https://x.test/u/a?code=${FILTERED}&mode=roast`);
    expect(asObject.request?.query_string).toEqual({ code: FILTERED, mode: "roast" });
    expect(asPairs.request?.query_string).toEqual([["state", FILTERED], ["page", "2"]]);
  });

  it("filters query values in the Next.js request path, trace data, spans and breadcrumbs", () => {
    const data = () => ({
      "http.request.header.user_agent": "ua",
      "http.request.header.referer": "https://x.test/me?state=s",
      "http.request.header.x_vercel_ip_city": FILTERED,
      "http.request.header.cookie.si_session": "s",
      "http.response.header.set_cookie": "s",
      "http.request.body.data": "{}",
      "http.target": "/u/a?code=c&mode=roast",
      "url.query": "?token=t",
      "next.route": "/u/[username]",
    });
    const event = scrubEvent({
      type: "transaction",
      contexts: { trace: { data: data() }, nextjs: { request_path: "/u/a?code=c" } },
      spans: [{ data: data() }],
      breadcrumbs: [{ category: "fetch", data: { url: "/_/backend/x?token=t", method: "GET" } }],
    } as unknown as Event);
    const expected = {
      "http.request.header.user_agent": "ua",
      "http.request.header.referer": `https://x.test/me?state=${FILTERED}`,
      "http.target": `/u/a?code=${FILTERED}&mode=roast`,
      "url.query": `?token=${FILTERED}`,
      "next.route": "/u/[username]",
    };
    const contexts = event.contexts as Record<string, Record<string, unknown>>;
    expect(contexts.trace.data).toEqual(expected);
    expect(contexts.nextjs.request_path).toBe(`/u/a?code=${FILTERED}`);
    expect((event as unknown as { spans: Array<{ data: unknown }> }).spans[0].data).toEqual(expected);
    expect(event.breadcrumbs?.[0].data).toEqual({ url: `/_/backend/x?token=${FILTERED}`, method: "GET" });
  });

  it.each([
    [{ request: null }, {}],
    [{ request: "x" }, {}],
    [{ request: { headers: [["cookie", "s"]] } }, { request: {} }],
    [{ request: { query_string: 3 } }, { request: {} }],
    [{ request: { url: 7 } }, { request: {} }],
    [{ user: "x" }, {}],
    [{ contexts: 1 }, {}],
    [{ contexts: { trace: { data: "x" } } }, { contexts: { trace: {} } }],
    [{ spans: "x" }, {}],
    [{ spans: [{ data: 1 }] }, { spans: [{}] }],
    [{ breadcrumbs: 5 }, {}],
    [{ breadcrumbs: [{ data: null }] }, { breadcrumbs: [{}] }],
  ])("drops a part it cannot read: %j", (input, expected) => {
    expect(scrubEvent(structuredClone(input) as unknown as Event)).toEqual(expected);
  });

  it("drops only the part it cannot read", () => {
    const event = scrubEvent({
      request: { headers: "not-a-dict", url: "https://x.test/a?code=c" },
      contexts: { auth: { access_token: "t", kept: "yes" } },
      message: "boom",
    } as unknown as Event);
    expect(event).toEqual({
      request: { url: `https://x.test/a?code=${FILTERED}` },
      contexts: { auth: { kept: "yes" } },
      message: "boom",
    });
  });

  it("leaves an event without request details unchanged", () => {
    const input = { message: "hi", level: "error", tags: { request_id: "r" }, request: { method: "GET" } };
    expect(scrubEvent(structuredClone(input) as unknown as Event)).toEqual(input);
  });

  it("the SDK's own request pipeline, then scrubEvent, leaks nothing for a signed-in request", () => {
    const client = { getDataCollectionOptions: () => SENTRY_DATA_COLLECTION };
    const headers = signedInHeaders();
    const processEvent = requestDataIntegration().processEvent!;
    const event = processEvent(
      {
        type: "transaction",
        sdkProcessingMetadata: {
          normalizedRequest: {
            headers,
            method: "GET",
            url: `https://skillissue.tech/u/octocat?code=${CANARIES.code}&state=${CANARIES.state}`,
            query_string: `code=${CANARIES.code}&state=${CANARIES.state}`,
            data: CANARIES.body,
          },
          ipAddress: CANARIES.ip,
        },
        contexts: {
          trace: { data: httpHeadersToSpanAttributes(headers, SENTRY_DATA_COLLECTION as never, "request") },
        },
      } as Event,
      {},
      client as never,
    ) as Event;

    // The constant already stops these at the source.
    expect(event.request?.cookies).toBeUndefined();
    expect(event.user?.ip_address).toBeUndefined();
    // scrubEvent removes everything else. sdkProcessingMetadata is the SDK's
    // internal copy of the raw request; the SDK strips it before sending.
    const sent: Record<string, unknown> = { ...scrubEvent(event) };
    delete sent.sdkProcessingMetadata;
    expect(leaks(sent)).toEqual([]);
    expect(event.request?.headers).toEqual({
      "user-agent": "canary-agent",
      referer: `https://skillissue.tech/me?code=${FILTERED}`,
    });
  });
});

describe("filterQuery and filterUrl", () => {
  it("leaves the app's own parameters alone", () => {
    expect(filterQuery("auth=failed&sort=new&page=2&mode=roast")).toBe("auth=failed&sort=new&page=2&mode=roast");
  });

  it("leaves URL edge cases intact", () => {
    expect(filterUrl("https://x.test/a?code=c#frag")).toBe(`https://x.test/a?code=${FILTERED}#frag`);
    expect(filterUrl("https://x.test/a?code&mode=roast")).toBe("https://x.test/a?code&mode=roast");
    expect(filterUrl("https://x.test/a?")).toBe("https://x.test/a?");
    expect(filterUrl("https://x.test/a")).toBe("https://x.test/a");
  });

  it("filters already-encoded values whole", () => {
    expect(filterQuery("code=a%2Fb%3D&mode=r%C3%B6ast")).toBe(`code=${FILTERED}&mode=r%C3%B6ast`);
  });
});
