import { Activity } from "react";
import { fireEvent, render, screen, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

import { HistoryGrid } from "../history-grid";
import type { SavedAnalysis } from "@/types";

function analysis(id: number, login: string): SavedAnalysis {
  return {
    id,
    target_login: login,
    is_public: false,
    share_slug: null,
    latest_run: {
      total_score: 73,
      tier_name: "Senior Engineer",
      completed_at: new Date("2026-07-31T00:00:00Z").toISOString(),
    },
  };
}

const analyses: SavedAnalysis[] = [analysis(1, "octocat")];

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

// Under `cacheComponents: true` the App Router hides /me behind React's
// <Activity> rather than unmounting it, so `useState(analyses)` keeps its
// original seed and never sees the server's newer list.
describe("HistoryGrid under Activity (Next 16 Cache Components)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    refresh.mockReset();
    global.fetch = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
  });
  afterEach(() => vi.useRealTimers());

  function Host({ mode, list }: { mode: "visible" | "hidden"; list: SavedAnalysis[] }) {
    return (
      <Activity mode={mode}>
        <HistoryGrid analyses={list} />
      </Activity>
    );
  }

  it("picks up an analysis saved elsewhere after a hide -> show cycle", () => {
    const before = [analysis(1, "octocat")];
    const after = [analysis(1, "octocat"), analysis(2, "shaan-alpha")];

    const { rerender } = render(<Host mode="visible" list={before} />);
    expect(screen.getByText("@octocat")).toBeInTheDocument();

    // Navigate away, save a new analysis, navigate back: the server now sends
    // two rows.
    act(() => rerender(<Host mode="hidden" list={after} />));
    act(() => rerender(<Host mode="visible" list={after} />));

    expect(screen.getByText("@shaan-alpha")).toBeInTheDocument();
    expect(screen.getByText("@octocat")).toBeInTheDocument();
  });

  it("drops an analysis deleted elsewhere after a hide -> show cycle", () => {
    const before = [analysis(1, "octocat"), analysis(2, "shaan-alpha")];
    const after = [analysis(1, "octocat")];

    const { rerender } = render(<Host mode="visible" list={before} />);
    expect(screen.getByText("@shaan-alpha")).toBeInTheDocument();

    act(() => rerender(<Host mode="hidden" list={after} />));
    act(() => rerender(<Host mode="visible" list={after} />));

    expect(screen.queryByText("@shaan-alpha")).not.toBeInTheDocument();
  });

  it("a resync does not resurrect a card inside its undo window", () => {
    const before = [analysis(1, "octocat")];
    const { rerender } = render(<Host mode="visible" list={before} />);

    fireEvent.click(screen.getByRole("button", { name: /delete @octocat/i }));
    expect(screen.queryByText("@octocat")).not.toBeInTheDocument();

    // A server payload arriving mid-window still lists the row — its DELETE
    // has not been sent yet. The optimistic removal must survive.
    const withNewRow = [analysis(1, "octocat"), analysis(2, "shaan-alpha")];
    act(() => rerender(<Host mode="visible" list={withNewRow} />));

    expect(screen.queryByText("@octocat")).not.toBeInTheDocument();
    expect(screen.getByText("@shaan-alpha")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /undo/i })).toBeInTheDocument();
  });

  it("does not reset the list when the prop identity changes but content does not", () => {
    const { rerender } = render(<Host mode="visible" list={[analysis(1, "octocat")]} />);
    fireEvent.click(screen.getByRole("button", { name: /delete @octocat/i }));
    expect(screen.queryByText("@octocat")).not.toBeInTheDocument();

    // Same content, brand-new array identity (a fresh server render).
    act(() => rerender(<Host mode="visible" list={[analysis(1, "octocat")]} />));

    expect(screen.queryByText("@octocat")).not.toBeInTheDocument();
  });
});
