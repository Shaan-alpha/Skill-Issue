import { fireEvent, render, screen, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

import { HistoryGrid } from "../history-grid";
import type { SavedAnalysis } from "@/types";

const analyses: SavedAnalysis[] = [
  {
    id: 1,
    target_login: "octocat",
    is_public: false,
    share_slug: null,
    latest_run: {
      total_score: 73,
      tier_name: "Senior Engineer",
      completed_at: new Date().toISOString(),
    },
  },
];

describe("HistoryGrid", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    refresh.mockReset();
    global.fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
  });
  afterEach(() => vi.useRealTimers());

  it("delete -> undo restores the card and issues no DELETE", async () => {
    render(<HistoryGrid analyses={analyses} />);
    fireEvent.click(screen.getByRole("button", { name: /delete @octocat/i }));

    // Card hidden, toast shown.
    expect(screen.queryByText("@octocat")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /undo/i }));

    expect(screen.getByText("@octocat")).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(6000));
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("delete -> timeout issues DELETE /analyses/{id}", async () => {
    render(<HistoryGrid analyses={analyses} />);
    fireEvent.click(screen.getByRole("button", { name: /delete @octocat/i }));

    await act(async () => {
      vi.advanceTimersByTime(5000);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/analyses/1"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
