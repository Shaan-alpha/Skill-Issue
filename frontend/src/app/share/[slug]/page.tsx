import { notFound } from "next/navigation";
import { ResultsView } from "@/components/results-view";
import { ShareAttribution } from "@/components/share-attribution";
import type { SharedAnalysisPayload } from "@/types";

export const metadata = { robots: "noindex, nofollow" };
export const dynamic = "force-dynamic";

async function loadShared(slug: string): Promise<SharedAnalysisPayload> {
  const r = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/share/${slug}`, {
    cache: "no-store",
  });
  if (r.status === 404) notFound();
  if (!r.ok) throw new Error("Failed to load shared analysis");
  return r.json();
}

export default async function SharePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const data = await loadShared(slug);
  return (
    <main className="container mx-auto max-w-6xl pt-24 pb-20 px-4 sm:px-6">
      <div className="mb-6">
        <ShareAttribution login={data.owner.login} avatarUrl={data.owner.avatar_url} />
      </div>
      <ResultsView report={data.report} username={data.report.username} sharedNarrative />
    </main>
  );
}
