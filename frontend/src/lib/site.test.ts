import { describe, expect, it } from "vitest";
import pkg from "../../package.json";
import { APP_VERSION } from "./site";

describe("APP_VERSION (v1.0.7 drift guard)", () => {
  it("matches package.json version so the UI never shows a stale release", () => {
    expect(APP_VERSION).toBe(pkg.version);
  });
});
