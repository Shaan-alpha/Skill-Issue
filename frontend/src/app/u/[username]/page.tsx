import { cookies, headers } from "next/headers";
import { notFound } from "next/navigation";
import { ResultsView } from "@/components/results-view";
import { NotAnIndividual } from "@/components/not-an-individual";
import { RateLimited } from "@/components/rate-limited";
import { Report } from "@/types";

interface AuthHints {
  analysisId: number | null;
  shareSlug: string | null;
}

// Backend returns 422 with { detail } when /users/{login} resolves to an
// Organization (or other non-User type). We surface the message directly
// instead of routing through error.tsx — Next.js error boundaries strip
// the actual response detail in prod and would show the generic "API may
// be down" copy, which is misleading for a deterministic input error.
type AnalysisResult =
  | { kind: "ok"; report: Report }
  | { kind: "not_individual"; detail: string }
  | { kind: "rate_limited"; retryAfterSeconds: number };

async function getAnalysis(
  username: string,
  cookieHeader: string,
): Promise<AnalysisResult> {
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  // Forward the real client IP + a shared secret so the backend can attribute
  // proxied anonymous /analyze requests to the visitor (not this RSC's egress
  // IP). The secret is server-only — never NEXT_PUBLIC.
  const h = await headers();
  const clientIp =
    h.get("x-forwarded-for")?.split(",")[0]?.trim() || h.get("x-real-ip") || "";
  const proxySecret = process.env.INTERNAL_PROXY_SECRET || "";

  const fwd: Record<string, string> = {};
  if (cookieHeader) fwd["cookie"] = cookieHeader;
  if (proxySecret) fwd["x-internal-secret"] = proxySecret;
  if (clientIp) fwd["x-client-ip"] = clientIp;

  const res = await fetch(`${baseUrl}/analyze/${encodeURIComponent(username)}`, {
    cache: "no-store",
    headers: fwd,
  });

  if (res.status === 404 || res.status === 400) notFound();
  if (res.status === 429) {
    let retryAfterSeconds = 3600;
    try {
      const body = (await res.json()) as { retry_after_seconds?: number };
      if (typeof body.retry_after_seconds === "number") {
        retryAfterSeconds = body.retry_after_seconds;
      }
    } catch {
      // fall through with the default
    }
    return { kind: "rate_limited", retryAfterSeconds };
  }
  if (res.status === 422) {
    let detail = `'${username}' is a GitHub organization, not a user.`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // fall through with the default message
    }
    return { kind: "not_individual", detail };
  }
  if (!res.ok) throw new Error(`Backend returned ${res.status}`);

  return { kind: "ok", report: (await res.json()) as Report };
}

async function loadAuthHints(
  username: string,
  cookieHeader: string,
): Promise<AuthHints> {
  if (!cookieHeader.includes("si_session")) {
    return { analysisId: null, shareSlug: null };
  }
  try {
    const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const r = await fetch(
      `${baseUrl}/me/analyses?sort=recent&page=1`,
      { headers: { cookie: cookieHeader }, cache: "no-store" },
    );
    if (!r.ok) return { analysisId: null, shareSlug: null };
    const body = (await r.json()) as {
      analyses: Array<{ id: number; target_login: string; share_slug: string | null }>;
    };
    const needle = username.toLowerCase();
    const match = body.analyses.find(
      (a) => a.target_login.toLowerCase() === needle,
    );
    return {
      analysisId: match?.id ?? null,
      shareSlug: match?.share_slug ?? null,
    };
  } catch {
    return { analysisId: null, shareSlug: null };
  }
}

export default async function AnalysisPage({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  const result = await getAnalysis(username, cookieHeader);
  if (result.kind === "not_individual") {
    return <NotAnIndividual username={username} detail={result.detail} />;
  }
  if (result.kind === "rate_limited") {
    return <RateLimited retryAfterSeconds={result.retryAfterSeconds} />;
  }

  const { report } = result;
  // Use the canonical login from the backend response, not the URL slug —
  // GitHub logins are case-insensitive in URLs but the backend stores the
  // canonical case (e.g. URL `/u/shaan-alpha`, stored target_login
  // `Shaan-alpha`). Matching by the URL slug would miss the row and leave
  // the share button disabled.
  const { analysisId, shareSlug } = await loadAuthHints(
    report.username,
    cookieHeader,
  );

  return (
    <ResultsView
      report={report}
      username={username}
      analysisId={analysisId}
      initialShareSlug={shareSlug}
    />
  );
}
