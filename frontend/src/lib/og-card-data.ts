import "server-only";
import { cacheLife, cacheTag } from "next/cache";
import type { Report, SharedAnalysisPayload } from "@/types";

function backendBase(): string {
  return (
    process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ??
    "http://localhost:8000"
  );
}

export async function fetchReportForUser(username: string): Promise<Report | null> {
  try {
    const r = await fetch(
      `${backendBase()}/analyze/${encodeURIComponent(username)}`,
      { cache: "no-store" },
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
// revoked slug 404s on the next request with no stale window.
//
// `cacheLife({ revalidate: 3600 })` is a fallback only — the webhook is
// the primary invalidation path. The 1-hour TTL bounds staleness if the
// webhook ever silently fails.
//
// 404/non-OK is NOT cached (we return null + don't tag), so the next visit
// retries the backend. This keeps a re-share with a brand-new slug working
// on first hit.
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
