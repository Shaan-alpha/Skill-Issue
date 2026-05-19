import "server-only";
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

export async function fetchReportForSlug(slug: string): Promise<Report | null> {
  try {
    const r = await fetch(
      `${backendBase()}/share/${encodeURIComponent(slug)}`,
      { cache: "no-store" },
    );
    if (!r.ok) return null;
    const payload = (await r.json()) as SharedAnalysisPayload;
    return payload.report;
  } catch {
    return null;
  }
}
