import { Activity } from "react";
import { act, render } from "@testing-library/react";
import { LazyMotion, domAnimation } from "framer-motion";
import { afterEach, describe, expect, it, vi } from "vitest";

import { NarrativeStream } from "../narrative-stream";

const instances: FakeES[] = [];

class FakeES {
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  closed = false;
  constructor(public url: string) {
    instances.push(this);
  }
  close() {
    this.closed = true;
  }
}

const NARRATIVE = "One hundred external PRs merged across seven organisations.";

function streamFullNarrative(es: FakeES) {
  act(() => {
    es.onmessage?.({ data: JSON.stringify({ chunk: NARRATIVE }) } as MessageEvent);
    es.onmessage?.({ data: JSON.stringify({ done: true }) } as MessageEvent);
  });
}

function occurrences(haystack: string, needle: string): number {
  return haystack.split(needle).length - 1;
}

function Host({ mode }: { mode: "visible" | "hidden" }) {
  return (
    <LazyMotion features={domAnimation}>
      <Activity mode={mode}>
        <NarrativeStream username="octocat" mode="roast" />
      </Activity>
    </LazyMotion>
  );
}

afterEach(() => {
  instances.length = 0;
  vi.unstubAllGlobals();
});

describe("NarrativeStream under Activity (Next 16 Cache Components)", () => {
  it("renders the narrative exactly once on a normal stream", () => {
    vi.stubGlobal("EventSource", FakeES as unknown as typeof EventSource);
    const { container } = render(<Host mode="visible" />);

    streamFullNarrative(instances[0]);

    expect(occurrences(container.textContent ?? "", NARRATIVE)).toBe(1);
  });

  it("does not stack a second copy after a hide -> show cycle (back/forward)", () => {
    vi.stubGlobal("EventSource", FakeES as unknown as typeof EventSource);
    const { container, rerender } = render(<Host mode="visible" />);

    streamFullNarrative(instances[0]);
    expect(occurrences(container.textContent ?? "", NARRATIVE)).toBe(1);

    // Back: Cache Components hides the route instead of unmounting it, so
    // effects tear down while useState survives.
    act(() => {
      rerender(<Host mode="hidden" />);
    });
    // Forward: the route becomes visible again and every effect re-runs.
    act(() => {
      rerender(<Host mode="visible" />);
    });

    // If the component reopens the stream, the backend narrative cache replays
    // the whole narrative in one chunk — that must replace, never append.
    if (instances.length > 1) {
      streamFullNarrative(instances[instances.length - 1]);
    }

    expect(occurrences(container.textContent ?? "", NARRATIVE)).toBe(1);
  });

  it("still shows one copy after three hide -> show cycles", () => {
    vi.stubGlobal("EventSource", FakeES as unknown as typeof EventSource);
    const { container, rerender } = render(<Host mode="visible" />);
    streamFullNarrative(instances[0]);

    for (let i = 0; i < 3; i++) {
      act(() => {
        rerender(<Host mode="hidden" />);
      });
      act(() => {
        rerender(<Host mode="visible" />);
      });
      const latest = instances[instances.length - 1];
      if (!latest.closed && latest !== instances[0]) streamFullNarrative(latest);
    }

    expect(occurrences(container.textContent ?? "", NARRATIVE)).toBe(1);
  });
});
