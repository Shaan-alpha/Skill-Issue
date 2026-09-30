import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/auth", () => ({
  useSession: () => ({ user: { id: 1, login: "alice", name: "Alice", avatar_url: null } }),
  signIn: vi.fn(),
}));
vi.mock("@/observability/events", () => ({ trackShareToggled: vi.fn() }));

import { SaveShareControls } from "../save-share-controls";

const revokeButton = () => screen.getByRole("button", { name: /click to revoke/i });

describe("SaveShareControls", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("keeps the link public, and says so, when revoking fails", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 403 }));
    render(<SaveShareControls initialShareSlug="abc123def456" analysisId={7} username="octocat" />);

    await act(async () => {
      fireEvent.click(revokeButton());
    });

    expect(screen.getByText(/still public/i)).toBeInTheDocument();
    expect(revokeButton()).toBeInTheDocument();
  });

  it("reports a failed share instead of doing nothing", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 500 }));
    render(<SaveShareControls initialShareSlug={null} analysisId={7} username="octocat" />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /^share$/i }));
    });

    expect(screen.getByText(/couldn't create a share link/i)).toBeInTheDocument();
  });

  it("reports a network failure without changing anything", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    render(<SaveShareControls initialShareSlug="abc123def456" analysisId={7} username="octocat" />);

    await act(async () => {
      fireEvent.click(revokeButton());
    });

    expect(screen.getByText(/nothing changed/i)).toBeInTheDocument();
    expect(revokeButton()).toBeInTheDocument();
  });
});
