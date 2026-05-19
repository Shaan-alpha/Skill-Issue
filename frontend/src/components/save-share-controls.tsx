"use client";

import { Check, Image as ImageIcon, Link2, LogIn, Share2 } from "lucide-react";
import { useState } from "react";

import { signIn, useSession } from "@/lib/auth";
import type { ShareResponse } from "@/types";

interface Props {
  /** Pre-existing share slug, if any. */
  initialShareSlug: string | null;
  /** Server-supplied analysis id for the current target. */
  analysisId: number | null;
  /** Canonical username for the analysis (drives the Share-card link). */
  username: string;
}

function backendUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ?? "";
  return `${base}${path}`;
}

export function SaveShareControls({ initialShareSlug, analysisId, username }: Props) {
  const session = useSession();
  const [shareSlug, setShareSlug] = useState<string | null>(initialShareSlug);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  // Anonymous viewers see a sign-in CTA so the feature is discoverable.
  if (!session) {
    return (
      <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-white/5 bg-card/30 px-4 py-3 text-sm">
        <span className="text-muted-foreground">
          Sign in to save this analysis to your history and share it with a link.
        </span>
        <button
          type="button"
          onClick={signIn}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 text-xs font-medium hover:bg-card/80 transition-colors"
        >
          <LogIn className="size-3.5" aria-hidden="true" />
          Sign in with GitHub
        </button>
      </div>
    );
  }

  async function toggleShare() {
    if (!analysisId) return;
    setBusy(true);
    try {
      const url = backendUrl(`/analyses/${analysisId}/share`);
      if (shareSlug) {
        await fetch(url, { method: "DELETE", credentials: "include" });
        setShareSlug(null);
        setToast("Share revoked");
      } else {
        const r = await fetch(url, { method: "POST", credentials: "include" });
        if (r.ok) {
          const body: ShareResponse = await r.json();
          setShareSlug(body.share_slug);
          try {
            await navigator.clipboard.writeText(body.share_url);
            setToast("Share URL copied to clipboard");
          } catch {
            setToast("Share link ready");
          }
        }
      }
    } finally {
      setBusy(false);
      setTimeout(() => setToast(null), 3000);
    }
  }

  return (
    <div
      className="mt-4 flex flex-wrap items-center gap-2 rounded-2xl border border-white/5 bg-card/30 px-4 py-3"
      role="status"
      aria-live="polite"
    >
      <span className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 text-xs font-medium text-emerald-300">
        <Check className="size-3.5" aria-hidden="true" />
        Saved to your history
      </span>
      <button
        type="button"
        onClick={toggleShare}
        disabled={busy || !analysisId}
        aria-pressed={!!shareSlug}
        className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 ${
          shareSlug
            ? "bg-accent/20 border border-accent/30 text-accent"
            : "bg-card/60 border border-border hover:bg-card/80"
        }`}
      >
        {shareSlug ? (
          <>
            <Link2 className="size-3.5" aria-hidden="true" />
            Shared — click to revoke
          </>
        ) : (
          <>
            <Share2 className="size-3.5" aria-hidden="true" />
            Share
          </>
        )}
      </button>
      <a
        href={`/u/${encodeURIComponent(username)}/card`}
        className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 text-xs font-medium hover:bg-card/80 transition-colors"
      >
        <ImageIcon className="size-3.5" aria-hidden="true" />
        Share card
      </a>
      {toast ? (
        <span className="text-xs text-muted-foreground sm:ml-auto">{toast}</span>
      ) : null}
    </div>
  );
}
