"use client";

import { Copy, Download, Link2 } from "lucide-react";
import { useState } from "react";
import { trackShareCardCopied } from "@/observability/events";

interface Props {
  /** Path or absolute URL to the PNG. */
  imageUrl: string;
  /** Absolute URL of the parent page (used by Copy URL). */
  pageUrl: string;
}

export function CardActions({ imageUrl, pageUrl }: Props) {
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  }

  async function copyPng() {
    setBusy(true);
    try {
      const r = await fetch(imageUrl, { cache: "no-store" });
      const blob = await r.blob();
      if (
        "write" in navigator.clipboard &&
        typeof window.ClipboardItem !== "undefined"
      ) {
        await navigator.clipboard.write([
          new window.ClipboardItem({ "image/png": blob }),
        ]);
        trackShareCardCopied({ method: "png_clipboard" });
        flash("PNG copied to clipboard");
      } else {
        flash("Copy not supported — use Download");
      }
    } catch {
      flash("Copy failed");
    } finally {
      setBusy(false);
    }
  }

  async function copyUrl() {
    try {
      await navigator.clipboard.writeText(pageUrl);
      trackShareCardCopied({ method: "url" });
      flash("URL copied");
    } catch {
      flash("Copy failed");
    }
  }

  return (
    <div
      className="flex flex-wrap items-center gap-3"
      role="status"
      aria-live="polite"
    >
      <button
        type="button"
        onClick={copyPng}
        disabled={busy}
        className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 text-xs font-medium hover:bg-card/80 transition-colors disabled:opacity-50"
      >
        <Copy className="size-3.5" aria-hidden="true" />
        Copy PNG
      </button>
      <a
        href={imageUrl}
        download
        onClick={() => trackShareCardCopied({ method: "png_download" })}
        className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 text-xs font-medium hover:bg-card/80 transition-colors"
      >
        <Download className="size-3.5" aria-hidden="true" />
        Download PNG
      </a>
      <button
        type="button"
        onClick={copyUrl}
        className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-4 py-1.5 text-xs font-medium hover:bg-card/80 transition-colors"
      >
        <Link2 className="size-3.5" aria-hidden="true" />
        Copy URL
      </button>
      {toast ? (
        <span className="text-xs text-muted-foreground sm:ml-2">{toast}</span>
      ) : null}
    </div>
  );
}
