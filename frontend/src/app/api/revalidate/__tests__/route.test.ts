import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/cache", () => ({
  revalidateTag: vi.fn(),
}));

describe("POST /api/revalidate", () => {
  const realSecret = process.env.REVALIDATE_SECRET;

  beforeEach(() => {
    process.env.REVALIDATE_SECRET = "supersecret";
    vi.clearAllMocks();
  });

  afterEach(() => {
    process.env.REVALIDATE_SECRET = realSecret;
  });

  it("401 when X-Revalidate-Secret header is missing", async () => {
    const { POST } = await import("../route");
    const req = new Request("http://test/api/revalidate", {
      method: "POST",
      body: JSON.stringify({ tag: "share:abc" }),
    });
    const res = await POST(req);
    expect(res.status).toBe(401);
    const body = (await res.json()) as { error: string };
    expect(body.error).toBe("invalid_secret");
  });

  it("401 when secret does not match", async () => {
    const { POST } = await import("../route");
    const req = new Request("http://test/api/revalidate", {
      method: "POST",
      headers: { "X-Revalidate-Secret": "wrong" },
      body: JSON.stringify({ tag: "share:abc" }),
    });
    const res = await POST(req);
    expect(res.status).toBe(401);
  });

  it("400 when body is missing or malformed tag", async () => {
    const { POST } = await import("../route");
    const req = new Request("http://test/api/revalidate", {
      method: "POST",
      headers: { "X-Revalidate-Secret": "supersecret" },
      body: JSON.stringify({}),
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it("400 when tag does not match share: prefix", async () => {
    const { POST } = await import("../route");
    const req = new Request("http://test/api/revalidate", {
      method: "POST",
      headers: { "X-Revalidate-Secret": "supersecret" },
      body: JSON.stringify({ tag: "user:abc" }),
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it("204 + revalidateTag called for a valid request", async () => {
    const { revalidateTag } = await import("next/cache");
    const { POST } = await import("../route");
    const req = new Request("http://test/api/revalidate", {
      method: "POST",
      headers: { "X-Revalidate-Secret": "supersecret" },
      body: JSON.stringify({ tag: "share:abc123" }),
    });
    const res = await POST(req);
    expect(res.status).toBe(204);
    // Must use `{ expire: 0 }` for immediate invalidation — anything else
    // serves stale content via stale-while-revalidate and breaks the
    // revoked-slug-404s-immediately contract.
    expect(revalidateTag).toHaveBeenCalledWith("share:abc123", { expire: 0 });
  });
});
