"use client";

import Link from "next/link";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="container mx-auto max-w-2xl pt-32 pb-20 px-6 text-center">
      <h1 className="text-2xl font-bold mb-3">Couldn&apos;t load your history</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Something went wrong reaching the backend. Try again, or head back home.
      </p>
      <div className="flex gap-3 justify-center">
        <button onClick={reset} className="rounded-full bg-foreground text-background px-5 py-2 text-sm font-medium">
          Try again
        </button>
        <Link href="/" className="rounded-full border border-border px-5 py-2 text-sm">
          Home
        </Link>
      </div>
    </main>
  );
}
