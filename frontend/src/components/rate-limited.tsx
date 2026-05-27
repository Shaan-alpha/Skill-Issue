import Link from "next/link";
import { ArrowLeft, Gauge } from "lucide-react";

interface RateLimitedProps {
  retryAfterSeconds: number;
}

function retryHint(seconds: number): string {
  if (seconds <= 60) return "in under a minute";
  const minutes = Math.ceil(seconds / 60);
  return `in about ${minutes} minute${minutes === 1 ? "" : "s"}`;
}

// Server-rendered 429 state. Backend returns 429 + { error: "rate_limited",
// retry_after_seconds } when the per-IP / per-user hourly cap is exceeded. We
// surface an on-voice message instead of routing through error.tsx's generic
// "API may be down" copy, which would be misleading for a deliberate throttle.
export function RateLimited({ retryAfterSeconds }: RateLimitedProps) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center px-4 py-8 text-center sm:px-6">
      <div className="absolute inset-0 -z-10 bg-[linear-gradient(to_right,#80808005_1px,transparent_1px),linear-gradient(to_bottom,#80808005_1px,transparent_1px)] bg-[size:2rem_2rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)]" />

      <div className="glass w-full max-w-md space-y-6 rounded-3xl p-6 sm:p-10">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white/5">
          <Gauge className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className="space-y-3">
          <h1 className="text-2xl font-semibold">Slow down a sec</h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            You&apos;re analyzing faster than we can keep up. Try again {retryHint(retryAfterSeconds)}.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-white/90"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Try a username
          </Link>
        </div>
      </div>
    </div>
  );
}
