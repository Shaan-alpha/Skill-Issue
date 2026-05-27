import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { RateLimited } from "../rate-limited";

describe("RateLimited", () => {
  it("renders on-voice copy and a back-home CTA", () => {
    render(<RateLimited retryAfterSeconds={120} />);
    expect(screen.getByRole("heading", { name: /slow down/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /try a username/i })).toHaveAttribute("href", "/");
  });

  it("surfaces a human retry hint derived from retryAfterSeconds", () => {
    render(<RateLimited retryAfterSeconds={120} />);
    expect(screen.getByText(/2 minutes/i)).toBeInTheDocument();
  });
});
