import { Activity } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BadgeRow } from "../badge-row";
import type { Badge as BadgeT } from "@/types";

const badges: BadgeT[] = [
  { slug: "oss", name: "OSS Contributor", evidence: "10+ external PRs" },
];

/** True when the element or any ancestor is dropped out of the layout. */
function isDisplayNone(el: HTMLElement | null): boolean {
  for (let n: HTMLElement | null = el; n; n = n.parentElement) {
    if (n.style.display === "none") return true;
  }
  return false;
}

describe("BadgeRow accessibility", () => {
  // The trigger renders through `Badge`, which is a <span>. Base UI only adds
  // role="button" when it is told the rendered element is not a native button,
  // so without `nativeButton={false}` assistive tech sees an unlabelled span.
  it("exposes each badge as a button in the accessibility tree", () => {
    render(<BadgeRow badges={badges} />);

    expect(
      screen.getByRole("button", { name: /OSS Contributor/i }),
    ).toBeInTheDocument();
  });

  it("opens the evidence popover on click", () => {
    render(<BadgeRow badges={badges} />);

    fireEvent.click(screen.getByRole("button", { name: /OSS Contributor/i }));

    expect(screen.getByText("10+ external PRs")).toBeInTheDocument();
  });

  it("renders nothing when there are no badges", () => {
    const { container } = render(<BadgeRow badges={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("BadgeRow under Activity (Next 16 Cache Components)", () => {
  // Popover.Portal mounts into document.body, outside the Activity boundary,
  // so the boundary's `display: none` never reaches an open popup. A popover
  // pinned open when the user hits browser-back would otherwise stay painted
  // on top of the next route.
  it("does not leave an open popover painted after the route is hidden", async () => {
    function Host({ mode }: { mode: "visible" | "hidden" }) {
      return (
        <Activity mode={mode}>
          <BadgeRow badges={badges} />
        </Activity>
      );
    }

    const { rerender } = render(<Host mode="visible" />);
    fireEvent.click(screen.getByRole("button", { name: /OSS Contributor/i }));
    expect(isDisplayNone(screen.getByText("10+ external PRs"))).toBe(false);

    await act(async () => {
      rerender(<Host mode="hidden" />);
    });

    // Asserted on layout, not presence: the popup is portaled to
    // document.body, so "still in the document" holds either way. What must not
    // survive is it being painted over the route the user navigated to.
    // (jest-dom's toBeVisible is no help — happy-dom computes no layout, so it
    // reports the popup as not visible even while it is open.)
    expect(isDisplayNone(screen.getByText("10+ external PRs"))).toBe(true);
  });
});
