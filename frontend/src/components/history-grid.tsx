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
  // Original ordering, so Undo can re-insert a card at its place.
  const orderRef = useRef<number[]>(analyses.map((a) => a.id));

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
        next.sort(
          (a, b) => orderRef.current.indexOf(a.id) - orderRef.current.indexOf(b.id),
        );
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
