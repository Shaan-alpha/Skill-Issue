import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { ResultsView } from "@/components/results-view";
import { NotAnIndividual } from "@/components/not-an-individual";
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
  | { kind: "not_individual"; detail: string };

async function getAnalysis(
  username: string,
  cookieHeader: string,
): Promise<AnalysisResult> {
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  const res = await fetch(`${baseUrl}/analyze/${username}`, {
    cache: "no-store",
    headers: cookieHeader ? { cookie: cookieHeader } : undefined,
  });

  if (res.status === 404 || res.status === 400) notFound();
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
