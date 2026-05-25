import crypto from "node:crypto";
import { NextResponse } from "next/server";
import { revalidateTag } from "next/cache";

/**
 * Server-to-server webhook. Backend share-toggle endpoints POST here with
 * `{ tag: "share:<slug>" }` to bust the Next.js cache for a specific slug.
 *
 * Auth: `X-Revalidate-Secret` must match `process.env.REVALIDATE_SECRET`,
 * byte for byte, constant-time. Tag must match `^share:[A-Za-z0-9_-]{1,64}$`
 * so this endpoint can't be coerced into busting unrelated tags even if the
 * secret leaks.
 */

const TAG_RE = /^share:[A-Za-z0-9_-]{1,64}$/;

function timingSafeEqualStr(a: string, b: string): boolean {
  const ab = Buffer.from(a);
  const bb = Buffer.from(b);
  if (ab.length !== bb.length) return false;
  return crypto.timingSafeEqual(ab, bb);
}

export async function POST(req: Request): Promise<NextResponse> {
  const expected = process.env.REVALIDATE_SECRET;
  const presented = req.headers.get("x-revalidate-secret");

  if (!expected || !presented || !timingSafeEqualStr(presented, expected)) {
    return NextResponse.json({ error: "invalid_secret" }, { status: 401 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "bad_tag" }, { status: 400 });
  }
  if (!body || typeof body !== "object") {
    return NextResponse.json({ error: "bad_tag" }, { status: 400 });
  }
  const tag = (body as { tag?: unknown }).tag;
  if (typeof tag !== "string" || !TAG_RE.test(tag)) {
    return NextResponse.json({ error: "bad_tag" }, { status: 400 });
  }

  // `{ expire: 0 }` is the documented pattern for webhook-driven immediate
  // invalidation — the next request for this tag re-fetches from the backend
  // rather than serving stale content via stale-while-revalidate. Critical
  // for our revocation contract: a revoked slug must 404 on the next hit.
  revalidateTag(tag, { expire: 0 });
  return new NextResponse(null, { status: 204 });
}
