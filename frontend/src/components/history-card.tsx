import Link from "next/link";
import { X } from "lucide-react";
import type { SavedAnalysis } from "@/types";
import { RefreshButton } from "@/components/refresh-button";

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

export function HistoryCard({
  analysis,
  onDelete,
}: {
  analysis: SavedAnalysis;
  onDelete?: (id: number) => void;
}) {
  const run = analysis.latest_run;
  return (
    <Link
      href={`/u/${analysis.target_login}`}
      className="relative block rounded-2xl border border-border bg-card/40 p-5 hover:bg-card/60 transition-colors"
    >
      {onDelete && (
        <button
          type="button"
          aria-label={`Delete @${analysis.target_login}`}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onDelete(analysis.id);
          }}
          className="absolute right-2 top-2 rounded-full p-1 text-muted-foreground/60 hover:bg-white/5 hover:text-foreground"
        >
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      )}
      <div className="flex items-center justify-between mb-3 pr-6">
        <span className="text-sm font-medium text-foreground">@{analysis.target_login}</span>
        {analysis.is_public ? (
          <span className="text-[10px] uppercase tracking-wider text-accent">Public</span>
        ) : (
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Private
          </span>
        )}
      </div>
      {run ? (
        <>
          <div className="text-3xl font-bold tracking-tight text-foreground">{run.total_score}</div>
          <div className="mt-1 text-xs text-muted-foreground">{run.tier_name}</div>
          <div className="mt-3 flex items-center justify-between gap-2">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Updated {relativeTime(run.completed_at)}
            </span>
            <RefreshButton target={analysis.target_login} />
          </div>
        </>
      ) : (
        <div className="text-xs text-muted-foreground">No run yet</div>
      )}
    </Link>
  );
}
