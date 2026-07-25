import { afterEach, describe, expect, it, vi } from "vitest";
import { createNarrativeEventSource } from "./sse";

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

afterEach(() => {
  instances.length = 0;
  vi.restoreAllMocks();
});

describe("createNarrativeEventSource (v1.0.7 SI-33)", () => {
  it("a done sentinel completes the stream and closes it", () => {
    vi.stubGlobal("EventSource", FakeES as unknown as typeof EventSource);
    const onChunk = vi.fn();
    const onError = vi.fn();
    const onComplete = vi.fn();
    createNarrativeEventSource("octocat", "roast", onChunk, onError, onComplete);
    const es = instances[0];

    es.onmessage?.({ data: JSON.stringify({ chunk: "hi" }) } as MessageEvent);
    expect(onChunk).toHaveBeenCalledWith("hi");

    es.onmessage?.({ data: JSON.stringify({ done: true }) } as MessageEvent);
    expect(onComplete).toHaveBeenCalledTimes(1);
    expect(onError).not.toHaveBeenCalled();
    expect(es.closed).toBe(true);
  });

  it("onerror signals a failure (onError), not a completion", () => {
    vi.stubGlobal("EventSource", FakeES as unknown as typeof EventSource);
    const onError = vi.fn();
    const onComplete = vi.fn();
    createNarrativeEventSource("octocat", "roast", () => {}, onError, onComplete);
    const es = instances[0];

    es.onerror?.(new Event("error"));
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onComplete).not.toHaveBeenCalled();
    expect(es.closed).toBe(true);
  });
});
