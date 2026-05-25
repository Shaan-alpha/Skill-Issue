import { Suspense } from "react";
import { notFound } from "next/navigation";
import { ResultsView } from "@/components/results-view";
import { ShareAttribution } from "@/components/share-attribution";
import { fetchSharedPayload } from "@/lib/og-card-data";

export const metadata = { robots: "noindex, nofollow" };

// v0.8.6: dropped `export const dynamic = "force-dynamic"`. With Next 16
// Cache Components, all request-time data access (params resolution + the
// `share:<slug>` cached fetch) sits inside <Suspense> so the static shell
// can prerender. Backend share-toggle endpoints synchronously bust the tag
// via `/api/revalidate` so a revoked slug 404s on the next request with no
// stale window.

async function SharedContent({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const data = await fetchSharedPayload(slug);
  if (!data) notFound();
  return (
    <>
      <div className="mb-6">
        <ShareAttribution
          login={data.owner.login}
          avatarUrl={data.owner.avatar_url}
          cardHref={`/u/${encodeURIComponent(data.report.username)}/card`}
        />
      </div>
      <ResultsView report={data.report} username={data.report.username} sharedNarrative />
    </>
  );
}

function SharedSkeleton() {
  return (
    <div className="space-y-6" aria-hidden="true">
      <div className="h-12 w-64 rounded-lg bg-white/5" />
      <div className="h-96 rounded-2xl bg-white/5" />
    </div>
  );
}

export default function SharePage({ params }: { params: Promise<{ slug: string }> }) {
  return (
    <main className="container mx-auto max-w-6xl pt-24 pb-20 px-4 sm:px-6">
      <Suspense fallback={<SharedSkeleton />}>
        <SharedContent params={params} />
      </Suspense>
    </main>
  );
}
