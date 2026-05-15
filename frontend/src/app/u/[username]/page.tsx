import { Report } from "@/types";
import { ResultsView } from "@/components/results-view";
import { notFound } from "next/navigation";

async function getAnalysis(username: string): Promise<Report> {
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
  const res = await fetch(`${baseUrl}/analyze/${username}`, { cache: "no-store" });

  if (res.status === 404 || res.status === 400) notFound();
  if (!res.ok) throw new Error(`Backend returned ${res.status}`);

  return res.json();
}

export default async function AnalysisPage({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;
  const report = await getAnalysis(username);
  return <ResultsView report={report} />;
}
