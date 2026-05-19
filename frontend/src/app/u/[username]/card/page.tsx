import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CardActions } from "@/components/card-actions";
import { fetchReportForUser } from "@/lib/og-card-data";

interface PageProps {
  params: Promise<{ username: string }>;
}

export const dynamic = "force-dynamic";

export async function generateMetadata({ params }: PageProps) {
  const { username } = await params;
  return {
    title: `${username}'s Skill Issue card`,
    description: `Shareable Skill Issue scorecard for @${username}.`,
  };
}

function siteOrigin(): string {
  const fromEnv = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  return "https://skill-issue-tau.vercel.app";
}

export default async function CardPage({ params }: PageProps) {
  const { username } = await params;
  const report = await fetchReportForUser(username);
  if (!report) notFound();

  const imageUrl = `/u/${encodeURIComponent(report.username)}/opengraph-image`;
  const pageUrl = `${siteOrigin()}/u/${encodeURIComponent(report.username)}`;

  return (
    <main className="container mx-auto max-w-4xl pt-20 pb-16 px-4 sm:px-6">
      <Link
        href={`/u/${encodeURIComponent(report.username)}`}
        className="inline-flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="size-3.5" aria-hidden="true" />
        Back to report
      </Link>

      <h1 className="mt-6 text-2xl font-semibold tracking-tight sm:text-3xl">
        Your Skill Issue card
      </h1>
      <p className="mt-2 text-sm text-muted-foreground max-w-prose">
        Drop this anywhere — LinkedIn, X, Discord, your portfolio. Pasting the
        link to your report shows this card inline automatically.
      </p>

      <div className="mt-8 overflow-hidden rounded-2xl border border-white/5 bg-card/30">
        <div className="aspect-[1200/630] w-full">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl}
            alt={`Skill Issue scorecard for @${report.username}`}
            className="size-full object-cover"
          />
        </div>
      </div>

      <div className="mt-6">
        <CardActions imageUrl={imageUrl} pageUrl={pageUrl} />
      </div>
    </main>
  );
}
