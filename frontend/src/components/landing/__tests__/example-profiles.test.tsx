import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

// Render framer-motion's `m.*` as plain divs — motion components don't render
// reliably under happy-dom without a LazyMotion provider (project lesson,
// PROGRESS_LOG 2026-05-28 v0.9.3). We only need the DOM structure here.
vi.mock("framer-motion", () => ({
  m: new Proxy(
    {},
    {
      get:
        () =>
        ({ children, className }: { children?: React.ReactNode; className?: string }) => (
          <div className={className}>{children}</div>
        ),
    },
  ),
}));

import { ExampleProfiles } from "@/components/landing/example-profiles";

describe("ExampleProfiles", () => {
  it("renders six example cards linking to live reports", () => {
    render(<ExampleProfiles />);
    expect(screen.getByRole("link", { name: /Linus Torvalds/i })).toHaveAttribute(
      "href",
      "/u/torvalds",
    );
    expect(screen.getAllByRole("link")).toHaveLength(6);
  });
});
