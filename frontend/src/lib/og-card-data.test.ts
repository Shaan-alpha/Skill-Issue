import { afterEach, vi } from "vitest";
import { fetchReportForUser, fetchReportForSlug } from "./og-card-data";
import type { Report } from "@/types";

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
