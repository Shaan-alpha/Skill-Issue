import { afterEach, vi } from "vitest";
import { fetchReportForUser, fetchReportForSlug } from "./og-card-data";
import type { Report } from "@/types";

// Mutable header map the mocked next/headers reads at call time. `vi.hoisted`
// initializes it before the (hoisted) vi.mock factory runs.
const { hdrs } = vi.hoisted(() => ({ hdrs: new Map<string, string>() }));
vi.mock("next/headers", () => ({
  headers: async () => ({ get: (k: string) => hdrs.get(k.toLowerCase()) ?? null }),
}));

const fixtureReport: Report = {
  username: "octocat",
  tier: {
    name: "Senior Engineer",
    sub_rank: 47,
    band: [65, 80],
    next_tier: "Staff Engineer",
    pts_to_next: 12,
    prev_tier: "Professional Developer",
    pts_above_prev: 5,
  },
  badges: [
    { slug: "oss", name: "OSS Contributor", evidence: "10+ external PRs" },
    { slug: "pr", name: "PR Master", evidence: "200+ reviews" },
    { slug: "poly", name: "Polyglot", evidence: "5 active languages" },
  ],
  breakdown: {
    repo_quality: { points: 24, max_points: 30, evidence: [] },
    engineering_maturity: { points: 16, max_points: 20, evidence: [] },
    oss_collab: { points: 12, max_points: 15, evidence: [] },
    consistency: { points: 8, max_points: 10, evidence: [] },
    recruiter_signal: { points: 12, max_points: 15, evidence: [] },
    learning_trajectory: { points: 6, max_points: 10, evidence: [] },
  },
  total: 78,
  generated_at: "2026-05-19T12:00:00Z",
};

afterEach(() => {
  vi.restoreAllMocks();
  hdrs.clear();
  delete process.env.INTERNAL_PROXY_SECRET;
});

describe("fetchReportForUser", () => {
  it("returns the report on 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(
        new Response(JSON.stringify(fixtureReport), { status: 200 }),
      ),
    );
    const got = await fetchReportForUser("octocat");
    expect(got?.username).toBe("octocat");
    expect(got?.total).toBe(78);
  });

  it("returns null on 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(new Response("", { status: 404 })),
    );
    expect(await fetchReportForUser("ghost")).toBeNull();
  });

  it("returns null on network error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValueOnce(new Error("ECONNREFUSED")),
    );
    expect(await fetchReportForUser("octocat")).toBeNull();
  });

  // v1.0.5 SI-08: proxied OG/card ingests must be attributed to the visitor IP
  // and carry the internal proxy secret so the anon /analyze limiter applies.
  it("forwards x-client-ip + x-internal-secret when available", async () => {
    hdrs.set("x-forwarded-for", "1.2.3.4, 10.0.0.1");
    process.env.INTERNAL_PROXY_SECRET = "sekret";
    const fetchMock = vi.fn(async () => new Response("null", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchReportForUser("octocat");

    const init = (fetchMock.mock.calls[0] as unknown[])[1] as RequestInit;
    const sent = init.headers as Record<string, string>;
    expect(sent["x-client-ip"]).toBe("1.2.3.4");
    expect(sent["x-internal-secret"]).toBe("sekret");
  });

  it("omits attribution headers cleanly when secret + ip are absent", async () => {
    const fetchMock = vi.fn(async () => new Response("null", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await fetchReportForUser("octocat");

    const init = (fetchMock.mock.calls[0] as unknown[])[1] as RequestInit;
    const sent = init.headers as Record<string, string>;
    expect(sent["x-client-ip"]).toBeUndefined();
    expect(sent["x-internal-secret"]).toBeUndefined();
  });
});

describe("fetchReportForSlug", () => {
  it("unwraps the SharedAnalysisPayload to its report", async () => {
    const payload = {
      report: fixtureReport,
      owner: { login: "shaan", avatar_url: null },
      shared_at: "2026-05-19T12:00:00Z",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(
        new Response(JSON.stringify(payload), { status: 200 }),
      ),
    );
    const got = await fetchReportForSlug("abc123xyz789");
    expect(got?.username).toBe("octocat");
  });

  it("returns null on 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(new Response("", { status: 404 })),
    );
    expect(await fetchReportForSlug("missing")).toBeNull();
  });
});
