import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { ResultsView } from "@/components/results-view";
import { Report } from "@/types";

interface AuthHints {
  analysisId: number | null;
  shareSlug: string | null;
}

async function getAnalysis(username: string, cookieHeader: string): Promise<Report> {
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  const res = await fetch(`${baseUrl}/analyze/${username}`, {
    cache: "no-store",
    headers: cookieHeader ? { cookie: cookieHeader } : undefined,
  });

  if (res.status === 404 || res.status === 400) notFound();
  if (!res.ok) throw new Error(`Backend returned ${res.status}`);

  return res.json();
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
    const match = body.analyses.find((a) => a.target_login === username);
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

  const report = await getAnalysis(username, cookieHeader);
  const { analysisId, shareSlug } = await loadAuthHints(username, cookieHeader);

  return (
    <ResultsView
      report={report}
      username={username}
      analysisId={analysisId}
      initialShareSlug={shareSlug}
    />
  );
}
