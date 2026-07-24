import { describe, expect, it } from "vitest";
import { scrubHeaders, SCRUB_HEADER_NAMES } from "./scrub";

describe("scrubHeaders (v1.0.4 SI-11)", () => {
  it("strips internal secret and IP headers, keeps benign ones", () => {
    const out = scrubHeaders({
      "x-internal-secret": "s",
      "x-revalidate-secret": "s",
      "x-client-ip": "9.9.9.9",
      "x-forwarded-for": "9.9.9.9",
      "x-real-ip": "9.9.9.9",
      accept: "application/json",
    });
    expect(out).toEqual({ accept: "application/json" });
  });

  it("registers the new names in SCRUB_HEADER_NAMES", () => {
    for (const n of [
      "x-internal-secret",
      "x-revalidate-secret",
      "x-client-ip",
      "x-forwarded-for",
      "x-real-ip",
    ]) {
      expect(SCRUB_HEADER_NAMES.has(n)).toBe(true);
    }
  });
});
