import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BadgeRow } from "../badge-row";
import type { Badge as BadgeT } from "@/types";

const badges: BadgeT[] = [
  { slug: "oss", name: "OSS Contributor", evidence: "10+ external PRs" },
];

// There is deliberately no <Activity> test here. A jsdom probe suggested the
// popup — portaled to document.body, outside the Activity boundary — stayed
// painted after the route was hidden, and a fix was written for it. Checking
// that against real Chrome (CDP, client-side navigation via the search bar,
// then browser-back) showed the popup already reports
// `hiddenAncestor: true, painted: false` on unmodified main: React's
// `display: none` does reach the portal in a real browser. The jsdom result
// was an artifact of happy-dom's portal handling, so the fix was reverted
// rather than kept for a bug that does not exist. See docs/PROGRESS_LOG.md.

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
