import { Activity } from "react";
import { act, render } from "@testing-library/react";
import { LazyMotion, domAnimation } from "framer-motion";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Report } from "@/types";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/auth", () => ({ useSession: () => null, signIn: vi.fn() }));
vi.mock("@/components/narrative-card", () => ({
  NarrativeCard: () => <div data-testid="narrative-card" />,
}));

const trackAnalyzeSubmitted = vi.fn();
vi.mock("@/observability/events", () => ({
  trackAnalyzeSubmitted: (...args: unknown[]) => trackAnalyzeSubmitted(...args),
  trackShareToggled: vi.fn(),
  trackShareCardCopied: vi.fn(),
  trackModeToggled: vi.fn(),
  trackSignInClicked: vi.fn(),
  trackForceRefreshClicked: vi.fn(),
}));

import { ResultsView } from "../results-view";

const report: Report = {
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
  badges: [{ slug: "oss", name: "OSS Contributor", evidence: "10+ external PRs" }],
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

function Host({ mode }: { mode: "visible" | "hidden" }) {
  return (
    <LazyMotion features={domAnimation}>
      <Activity mode={mode}>
        <ResultsView report={report} username="octocat" analysisId={null} initialShareSlug={null} />
      </Activity>
    </LazyMotion>
  );
}

afterEach(() => {
  trackAnalyzeSubmitted.mockReset();
});

describe("ResultsView analytics under Activity (Next 16 Cache Components)", () => {
  it("reports analyze_submitted once per analysis, not once per re-show", () => {
    const { rerender } = render(<Host mode="visible" />);
    expect(trackAnalyzeSubmitted).toHaveBeenCalledTimes(1);

    // Three back/forward round trips: Cache Components hides the route rather
    // than unmounting it, so every effect re-runs on each re-show.
    for (let i = 0; i < 3; i++) {
      act(() => {
        rerender(<Host mode="hidden" />);
      });
      act(() => {
        rerender(<Host mode="visible" />);
      });
    }

    expect(trackAnalyzeSubmitted).toHaveBeenCalledTimes(1);
  });
});
