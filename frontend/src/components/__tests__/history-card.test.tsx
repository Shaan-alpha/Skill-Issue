import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh: vi.fn() }) }));

import { HistoryCard } from "../history-card";
import type { SavedAnalysis } from "@/types";

const analysis: SavedAnalysis = {
  id: 7,
  target_login: "octocat",
  is_public: false,
  share_slug: null,
  latest_run: {
    total_score: 73,
    tier_name: "Senior Engineer",
    completed_at: new Date("2026-10-01T00:00:00Z").toISOString(),
  },
};

describe("HistoryCard", () => {
  it("keeps its buttons outside the link that opens the report", () => {
    const { container } = render(<HistoryCard analysis={analysis} onDelete={() => {}} />);

    // A button inside <a> is invalid HTML: screen readers read it as part of
    // the link's name and keyboard focus lands inside the link.
    expect(container.querySelector("a button")).toBeNull();
    expect(screen.getByRole("link", { name: "@octocat" })).toHaveAttribute("href", "/u/octocat");
    expect(screen.getByRole("button", { name: "Delete @octocat" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();
  });

  it("deletes by id", () => {
    const onDelete = vi.fn();
    render(<HistoryCard analysis={analysis} onDelete={onDelete} />);

    fireEvent.click(screen.getByRole("button", { name: "Delete @octocat" }));

    expect(onDelete).toHaveBeenCalledWith(7);
  });
});
