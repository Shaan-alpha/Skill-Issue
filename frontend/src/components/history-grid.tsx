"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { HistoryCard } from "@/components/history-card";
import type { SavedAnalysis } from "@/types";

const UNDO_WINDOW_MS = 5000;

export function HistoryGrid({ analyses }: { analyses: SavedAnalysis[] }) {
  const router = useRouter();
  const [items, setItems] = useState<SavedAnalysis[]>(analyses);
  // The analysis currently in its undo window (removed from view, not yet deleted).
  const [pending, setPending] = useState<SavedAnalysis | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Server ordering, so Undo can re-insert a card at its place. State rather
  // than a ref because it is rewritten by the resync below, and writing a ref
  // during render is not allowed.
  const [order, setOrder] = useState<number[]>(() => analyses.map((a) => a.id));

  // `items` seeds from a prop, which used to be safe: navigating away unmounted
  // this route, so coming back remounted it and reseeded. Under
  // `cacheComponents: true` (next.config.ts) the App Router hides /me behind
  // React's <Activity> and keeps it alive for up to 3 routes, so the seed stuck
  // and an analysis saved elsewhere never showed up in the history. Resync on
  // the server list's *content*, not its identity — a fresh server render hands
  // us a new array every time, and resetting on that would wipe an in-flight
  // undo. This is React's documented "adjusting state when a prop changes"
  // pattern: a plain render-time computation, no effect and no extra paint.
  const signature = analyses.map((a) => a.id).join(",");
  const [syncedSignature, setSyncedSignature] = useState(signature);
  if (signature !== syncedSignature) {
    setSyncedSignature(signature);
    // Keep the optimistic removal: `pending`'s DELETE is still in flight, so
    // the server legitimately still lists it.
    setItems(pending ? analyses.filter((a) => a.id !== pending.id) : analyses);
    setOrder(analyses.map((a) => a.id));
  }

  function commitDelete(id: number) {
    void fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL ?? ""}/analyses/${id}`, {
      method: "DELETE",
      credentials: "include",
    })
      .catch(() => {})
      .finally(() => router.refresh());
  }

  function flushPending() {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    if (pending) commitDelete(pending.id);
    setPending(null);
  }

  function handleDelete(id: number) {
    // A second delete while one is pending commits the first immediately.
    flushPending();
    const target = items.find((a) => a.id === id);
    if (!target) return;
    setItems((prev) => prev.filter((a) => a.id !== id));
    setPending(target);
    timer.current = setTimeout(() => {
      commitDelete(target.id);
      setPending(null);
      timer.current = null;
    }, UNDO_WINDOW_MS);
  }

  function handleUndo() {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    if (pending) {
      const restored = pending;
      setItems((prev) => {
        const next = [...prev, restored];
        next.sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
        return next;
      });
      setPending(null);
    }
  }

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((a) => (
          <HistoryCard key={a.id} analysis={a} onDelete={handleDelete} />
        ))}
      </div>
      {pending && (
        <div
          role="status"
          className="fixed inset-x-0 bottom-6 z-50 mx-auto flex w-fit items-center gap-3 rounded-full border border-border bg-card/90 px-4 py-2 text-sm shadow-lg backdrop-blur"
        >
          <span className="text-muted-foreground">Analysis removed</span>
          <button
            type="button"
            onClick={handleUndo}
            className="font-medium text-accent hover:underline"
          >
            Undo
          </button>
        </div>
      )}
    </>
  );
}
