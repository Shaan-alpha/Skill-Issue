import { render, screen } from "@testing-library/react";
import type { Report } from "@/types";
import { OgCard } from "./og-card";

function fixture(overrides: Partial<Report> = {}): Report {
  return {
    username: "octocat",
    tier: {
      name: "Senior Engineer",
      sub_rank: 47,
      band: [65, 80],
      next_tier: "Staff Engineer",
      pts_to_next: 8,
      prev_tier: "Professional Developer",
      pts_above_prev: 7,
    },
    badges: [
      { slug: "oss-contributor", name: "OSS Contributor", evidence: "x" },
      { slug: "pr-master", name: "PR Master", evidence: "y" },
      { slug: "polyglot", name: "Polyglot", evidence: "z" },
      { slug: "long-haul", name: "Long-haul", evidence: "w" },
    ],
    breakdown: {} as Report["breakdown"],
    total: 72,
    generated_at: "2026-05-19T00:00:00Z",
    ...overrides,
  };
}

describe("OgCard", () => {
  it("renders username and tier name", () => {
    render(<OgCard report={fixture()} />);
    expect(screen.getByText("octocat")).toBeInTheDocument();
    expect(screen.getByText("Senior Engineer")).toBeInTheDocument();
  });

  it("renders the total score prominently", () => {
    render(<OgCard report={fixture({ total: 72 })} />);
    expect(screen.getByText("72")).toBeInTheDocument();
    expect(screen.getByText("/ 100")).toBeInTheDocument();
  });

  it("renders up to 3 badges only", () => {
    render(<OgCard report={fixture()} />);
    expect(screen.getByText("OSS Contributor")).toBeInTheDocument();
    expect(screen.getByText("PR Master")).toBeInTheDocument();
    expect(screen.getByText("Polyglot")).toBeInTheDocument();
    expect(screen.queryByText("Long-haul")).not.toBeInTheDocument();
  });

  it("renders zero badges gracefully", () => {
    const r = fixture({ badges: [] });
    const { container } = render(<OgCard report={r} />);
    expect(
      container.querySelector("[data-testid='og-badge-row']"),
    ).toBeInTheDocument();
    expect(screen.queryByText("OSS Contributor")).not.toBeInTheDocument();
  });

  it("renders sub-rank caption", () => {
    render(<OgCard report={fixture()} />);
    expect(screen.getByText("47/100 within tier")).toBeInTheDocument();
  });

  it("renders next-tier caption when there is a next tier", () => {
    render(<OgCard report={fixture()} />);
    expect(
      screen.getByText("next: Staff Engineer · 8 pts"),
    ).toBeInTheDocument();
  });

  it("omits next-tier caption at Principal", () => {
    const r = fixture({
      tier: {
        name: "Principal Engineer",
        sub_rank: 95,
        band: [90, 100],
        next_tier: null,
        pts_to_next: null,
        prev_tier: "Staff Engineer",
        pts_above_prev: 5,
      },
    });
    render(<OgCard report={r} />);
    expect(screen.queryByText(/^next:/)).not.toBeInTheDocument();
  });

  it("renders brand mark", () => {
    render(<OgCard report={fixture()} />);
    expect(screen.getByText("Skill Issue")).toBeInTheDocument();
  });

  it("renders the CREATOR label when creator", () => {
    render(<OgCard report={fixture()} creator />);
    expect(screen.getByText(/CREATOR · SKILL ISSUE/i)).toBeInTheDocument();
  });

  it("omits the CREATOR label by default", () => {
    render(<OgCard report={fixture()} />);
    expect(screen.queryByText(/CREATOR · SKILL ISSUE/i)).not.toBeInTheDocument();
  });
});
