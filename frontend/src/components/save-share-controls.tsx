"use client";

import { useState } from "react";
import { useSession } from "@/lib/auth";
import type { ShareResponse } from "@/types";

interface Props {
  /** Pre-existing share slug, if any. */
  initialShareSlug: string | null;
  /** Server-supplied analysis id for the current target. */
  analysisId: number | null;
}

function backendUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ?? "";
  return `${base}${path}`;
}

export function SaveShareControls({
  initialShareSlug,
  analysisId,
}: Props) {
  const session = useSession();
  const [shareSlug, setShareSlug] = useState<string | null>(initialShareSlug);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  if (!session) return null;

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
    <div className="mt-4 flex items-center gap-2 flex-wrap" role="status" aria-live="polite">
      <span className="inline-flex items-center gap-2 rounded-full bg-card/40 border border-border px-3 py-1 text-xs">
        Saved
      </span>
      <button
        type="button"
        onClick={toggleShare}
        disabled={busy || !analysisId}
        aria-pressed={!!shareSlug}
        className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
          shareSlug
            ? "bg-accent text-accent-foreground"
            : "bg-card/40 border border-border hover:bg-card/60"
        } disabled:opacity-50`}
      >
        {shareSlug ? "Shared — click to revoke" : "Share"}
      </button>
      {toast ? (
        <span className="text-xs text-muted-foreground">{toast}</span>
      ) : null}
    </div>
  );
}
