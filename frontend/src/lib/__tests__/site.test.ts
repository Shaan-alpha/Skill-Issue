import { afterEach, describe, expect, it, vi } from "vitest";
import { siteHost, siteOrigin } from "../site";

describe("siteOrigin", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("prefers NEXT_PUBLIC_SITE_URL and strips a trailing slash", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://example.com/");
    expect(siteOrigin()).toBe("https://example.com");
  });

  it("falls back to the production domain when the env is unset", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "");
    expect(siteOrigin()).toBe("https://skillissue.tech");
  });
});

describe("siteHost", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("returns the origin without the protocol", () => {
    vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://skillissue.tech");
    expect(siteHost()).toBe("skillissue.tech");
  });
});
