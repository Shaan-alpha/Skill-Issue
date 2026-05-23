import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi, beforeEach, afterEach, describe, it, expect } from "vitest";

import { RefreshButton } from "../refresh-button";

describe("RefreshButton", () => {
  const realFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = realFetch;
  });

  it("clicking POSTs to /me/refresh/{target} and shows pending state", async () => {
    let resolveFetch!: (v: Response) => void;
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = resolve;
        }),
    );

    render(<RefreshButton target="octocat" />);
    const btn = screen.getByRole("button", { name: /refresh/i });
    fireEvent.click(btn);

    await waitFor(() => expect(btn).toBeDisabled());
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/me/refresh/octocat"),
      expect.objectContaining({ method: "POST" }),
    );

    resolveFetch(new Response(JSON.stringify({ ok: true }), { status: 200 }));
  });

  it("after 200 response, button re-enables and onRefreshed fires", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify({ username: "octocat", total: 73 }), { status: 200 }),
    );
    const onRefreshed = vi.fn();

    render(<RefreshButton target="octocat" onRefreshed={onRefreshed} />);
    fireEvent.click(screen.getByRole("button", { name: /refresh/i }));

    await waitFor(() => expect(onRefreshed).toHaveBeenCalledTimes(1));
    expect(onRefreshed).toHaveBeenCalledWith(
      expect.objectContaining({ username: "octocat", total: 73 }),
    );
  });

  it("on 429 response, button re-enables and shows the rate-limit hint", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: "rate_limited", retry_after_seconds: 1800 }),
        { status: 429 },
      ),
    );

    render(<RefreshButton target="octocat" />);
    const btn = screen.getByRole("button", { name: /refresh/i });
    fireEvent.click(btn);

    await waitFor(() => expect(btn).not.toBeDisabled());
    expect(screen.getByText(/rate limit/i)).toBeInTheDocument();
  });
});
