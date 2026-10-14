import { fireEvent, render, screen } from "@testing-library/react";
import { LazyMotion, domAnimation } from "framer-motion";
import { describe, expect, it, vi } from "vitest";

import type { Report } from "@/types";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/auth", () => ({ useSession: () => null, signIn: vi.fn() }));
vi.mock("@/components/narrative-card", () => ({ NarrativeCard: () => null }));
vi.mock("@/observability/events", () => ({
  trackAnalyzeSubmitted: vi.fn(),
  trackShareToggled: vi.fn(),
  trackSignInClicked: vi.fn(),
}));

import { ResultsView } from "../results-view";

const empty = { points: 0, evidence: [] };

const report: Report = {
  username: "octocat",
  tier: {
    name: "Student Builder",
    sub_rank: 0,
    band: [20, 35],
    next_tier: "Entry-Level Engineer",
    pts_to_next: 15,
    prev_tier: "Hobbyist",
    pts_above_prev: 0,
  },
  badges: [],
  breakdown: {
    repo_quality: {
      points: 14,
      max_points: 30,
      evidence: [
        { signal: "readme_majority", detail: "80% of non-fork repos have READMEs", weight: 6 },
        { signal: "testing_or_ci", detail: "At least one non-fork repo has tests or CI", weight: 8 },
        { signal: "readme_depth", detail: "READMEs average 3.0 KB across 2 repos", weight: 0 },
      ],
    },
    engineering_maturity: { ...empty, max_points: 20 },
    oss_collab: { ...empty, max_points: 15 },
    consistency: { ...empty, max_points: 10 },
    recruiter_signal: { ...empty, max_points: 15 },
    learning_trajectory: { ...empty, max_points: 10 },
  },
  total: 14,
  generated_at: "2026-10-13T00:00:00Z",
};

function renderReport() {
  render(
    <LazyMotion features={domAnimation}>
      <ResultsView report={report} username="octocat" analysisId={null} initialShareSlug={null} />
    </LazyMotion>,
  );
}

describe("score card evidence", () => {
  it("offers the evidence behind each card's points", () => {
    renderReport();
    expect(
      screen.getByRole("button", { name: "Why 14 of 30 points in Repo Quality" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("80% of non-fork repos have READMEs")).not.toBeInTheDocument();
  });

  it("lists each signal with the points it earned", () => {
    renderReport();
    fireEvent.click(screen.getByRole("button", { name: /points in Repo Quality/ }));

    expect(screen.getByText("80% of non-fork repos have READMEs")).toBeInTheDocument();
    expect(screen.getByText("+6")).toBeInTheDocument();
    expect(screen.getByText("+8")).toBeInTheDocument();
    // A context row earns nothing and says nothing about points.
    expect(screen.getByText("READMEs average 3.0 KB across 2 repos")).toBeInTheDocument();
    expect(screen.queryByText("+0")).not.toBeInTheDocument();
  });

  it("says plainly when a bucket earned nothing", () => {
    renderReport();
    fireEvent.click(screen.getByRole("button", { name: /points in Engineering Maturity/ }));

    expect(screen.getByText(/nothing in this bucket has earned points yet/i)).toBeInTheDocument();
  });
});
