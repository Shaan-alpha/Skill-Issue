import "server-only";
import { cacheLife, cacheTag } from "next/cache";
import { headers } from "next/headers";
import type { Report, SharedAnalysisPayload } from "@/types";

function backendBase(): string {
  return (
    process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ??
    "http://localhost:8000"
  );
}

export async function fetchReportForUser(username: string): Promise<Report | null> {
  // v1.0.5 SI-08: attribute proxied OG/card ingests to the real visitor IP and
  // carry the internal proxy secret, so these unauthenticated routes are subject
  // to the anon /analyze limiter instead of the shared Vercel-egress bucket.
  const h = await headers();
  const clientIp = (
    h.get("x-forwarded-for")?.split(",")[0] ??
    h.get("x-real-ip") ??
    ""
  ).trim();
  const fwd: Record<string, string> = {};
  const secret = process.env.INTERNAL_PROXY_SECRET; // server-only, never NEXT_PUBLIC
  if (secret) fwd["x-internal-secret"] = secret;
  if (clientIp) fwd["x-client-ip"] = clientIp;
  try {
    const r = await fetch(
      `${backendBase()}/analyze/${encodeURIComponent(username)}`,
      { cache: "no-store", headers: fwd },
    );
    if (!r.ok) return null;
    return (await r.json()) as Report;
  } catch {
    return null;
  }
}

// v0.8.6: cached on Next 16 Cache Components, tagged `share:<slug>`.
// Backend `POST /analyses/{id}/share` and `DELETE` schedule a webhook to
// `/api/revalidate` that calls `revalidateTag` with `{ expire: 0 }`, so a
// revoked slug returns the not-found body on the next request with no
// stale window (PPR caveat: HTTP status is 200 from the static shell — see
// PROGRESS_LOG 2026-05-25 v0.8.6 entry for the trade-off).
//
// `cacheLife({ revalidate: 3600 })` is a fallback only — the webhook is
// the primary invalidation path. The 1-hour TTL bounds staleness if the
// webhook ever silently fails.
//
// `null` results are tagged the same as successful payloads — so an
// unknown slug entry stays cached for 3600s (cheap DDoS defence against
// random slug enumeration). A real re-share with that exact slug would
// fire the webhook and bust the tag, but slug entropy (72-bit base64url)
// makes the collision case vanishingly rare.
export async function fetchSharedPayload(
  slug: string,
): Promise<SharedAnalysisPayload | null> {
  "use cache";
  cacheTag(`share:${slug}`);
  cacheLife({ revalidate: 3600 });
  try {
    const r = await fetch(`${backendBase()}/share/${encodeURIComponent(slug)}`);
    if (!r.ok) return null;
    return (await r.json()) as SharedAnalysisPayload;
  } catch {
    return null;
  }
}

export async function fetchReportForSlug(slug: string): Promise<Report | null> {
  const payload = await fetchSharedPayload(slug);
  return payload?.report ?? null;
}
