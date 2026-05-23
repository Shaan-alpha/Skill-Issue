"use client";

import { RefreshCw } from "lucide-react";
import { useState } from "react";

type Status = "idle" | "pending" | "error" | "rate_limited";

export type RefreshButtonProps = {
  target: string;
  onRefreshed?: (report: unknown) => void;
};

export function RefreshButton({ target, onRefreshed }: RefreshButtonProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleClick(e: React.MouseEvent) {
    // The button lives inside <Link href="/u/..."> — don't navigate.
    e.preventDefault();
    e.stopPropagation();
    if (status === "pending") return;

    setStatus("pending");
    setErrorMessage(null);
    const startedAt = performance.now();

    try {
      const r = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL ?? ""}/me/refresh/${encodeURIComponent(target)}`,
        { method: "POST", credentials: "include" },
      );
      const durationMs = Math.round(performance.now() - startedAt);

      if (r.status === 429) {
        const body = (await r.json().catch(() => ({}))) as {
          retry_after_seconds?: number;
        };
        const minutes = Math.ceil((body.retry_after_seconds ?? 60) / 60);
        setErrorMessage(`Rate limit — try again in ${minutes} min`);
        setStatus("rate_limited");
        const { trackForceRefreshClicked } = await import("@/observability/events");
        trackForceRefreshClicked({
          target_login: target,
          duration_ms: durationMs,
          success: false,
        });
        return;
      }
      if (!r.ok) {
        setErrorMessage(`Refresh failed (${r.status})`);
        setStatus("error");
        const { trackForceRefreshClicked } = await import("@/observability/events");
        trackForceRefreshClicked({
          target_login: target,
          duration_ms: durationMs,
          success: false,
        });
        return;
      }

      const report = await r.json();
      onRefreshed?.(report);
      setStatus("idle");
      const { trackForceRefreshClicked } = await import("@/observability/events");
      trackForceRefreshClicked({
        target_login: target,
        duration_ms: durationMs,
        success: true,
      });
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Refresh failed");
      setStatus("error");
    }
  }

  const pending = status === "pending";

  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={pending}
        className="inline-flex items-center gap-1 rounded-full border border-border px-3 py-1 text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground disabled:opacity-50"
        aria-label={pending ? "Refreshing" : "Refresh"}
      >
        <RefreshCw className={pending ? "h-3 w-3 animate-spin" : "h-3 w-3"} aria-hidden />
        {pending ? "Refreshing" : "Refresh"}
      </button>
      {errorMessage && (
        <span role="status" className="text-[10px] text-destructive">
          {errorMessage}
        </span>
      )}
    </div>
  );
}
