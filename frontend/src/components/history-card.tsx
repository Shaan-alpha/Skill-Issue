import Link from "next/link";
import type { SavedAnalysis } from "@/types";

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  const days = Math.floor(ms / 86400000);
  if (days < 1) return "today";
  if (days === 1) return "yesterday";
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} mo ago`;
  return `${Math.floor(months / 12)} yr ago`;
}

export function HistoryCard({ analysis }: { analysis: SavedAnalysis }) {
  const run = analysis.latest_run;
  return (
    <Link
      href={`/u/${analysis.target_login}`}
      className="block rounded-2xl border border-border bg-card/40 p-5 hover:bg-card/60 transition-colors"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-foreground">@{analysis.target_login}</span>
        {analysis.is_public ? (
          <span className="text-[10px] uppercase tracking-wider text-accent">Public</span>
        ) : (
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Private</span>
        )}
      </div>
      {run ? (
        <>
          <div className="text-3xl font-bold tracking-tight text-foreground">{run.total_score}</div>
          <div className="mt-1 text-xs text-muted-foreground">{run.tier_name}</div>
          <div className="mt-3 text-[10px] uppercase tracking-wider text-muted-foreground">
            Updated {relativeTime(run.completed_at)}
          </div>
        </>
      ) : (
        <div className="text-xs text-muted-foreground">No run yet</div>
      )}
    </Link>
  );
}
