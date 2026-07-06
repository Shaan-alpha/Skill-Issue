import { Skeleton } from "@/components/ui/skeleton";

// Skeleton structure mirrors ResultsView's render order exactly so the
// skeleton→real swap doesn't shift the layout. Sections, in order:
//   1. Header (back link + Badge + ExternalLink)
//   2. SaveShareControls (left) + SearchBar (right); stacked on mobile
//   3. PositionBar (tier + progress bar)
//   4. BadgeRow (3-5 chips)
//   5. Aggregate-score panel + Engineering-report panel (lg:grid-cols-3)
//   6. NarrativeCard (controls + streaming text area)
//   7. Scoring matrix (6 cards)
//   8. Footer (version line)
export default function Loading() {
  return (
    <div className="min-h-screen bg-background px-4 py-6 sm:px-6 sm:py-12">
      <main className="mx-auto max-w-6xl animate-in space-y-8 sm:space-y-12">
        <h1 className="sr-only">Loading engineering report&hellip;</h1>
        {/* 1. Header */}
        <header className="flex flex-wrap items-center justify-between gap-3">
          <Skeleton className="h-4 w-28 bg-white/5" />
          <div className="flex items-center gap-3">
            <Skeleton className="h-6 w-32 bg-white/5" />
            <Skeleton className="h-8 w-8 rounded-full bg-white/5" />
          </div>
        </header>

        {/* 2. SaveShareControls (left, anonymous CTA height) + SearchBar (right) */}
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-white/5 bg-card/30 px-4 py-3">
            <Skeleton className="h-4 w-72 max-w-full bg-white/5" />
            <Skeleton className="h-7 w-36 rounded-full bg-white/5" />
          </div>
          <div className="flex justify-center sm:justify-end lg:flex-1">
            <div className="w-full max-w-md space-y-2">
              <div className="flex items-center gap-2">
                <Skeleton className="h-12 flex-1 rounded-lg bg-white/5" />
                <Skeleton className="h-12 w-12 rounded-lg bg-white/5" />
              </div>
              <Skeleton className="h-5 w-64 max-w-full bg-white/5" />
            </div>
          </div>
        </div>

        {/* 3. PositionBar */}
        <section className="glass space-y-3 rounded-2xl p-4 sm:p-6">
          <div className="flex items-baseline justify-between">
            <Skeleton className="h-4 w-40 bg-white/5" />
            <Skeleton className="h-3 w-24 bg-white/5" />
          </div>
          <Skeleton className="h-2 w-full rounded-full bg-white/5" />
          <div className="flex justify-between">
            {Array.from({ length: 7 }).map((_, i) => (
              <Skeleton key={i} className="h-3 w-8 bg-white/5" />
            ))}
          </div>
        </section>

        {/* 4. BadgeRow */}
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-6 w-24 rounded-full bg-white/5" />
          ))}
        </div>

        {/* 5. Aggregate-score panel + Engineering-report panel */}
        <section className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8">
          <div className="glass flex flex-col items-center justify-center space-y-4 rounded-3xl p-6 text-center sm:p-8 lg:col-span-1">
            <Skeleton className="h-4 w-32 bg-white/5" />
            <Skeleton className="h-36 w-36 rounded-full bg-white/5 sm:h-48 sm:w-48" />
            <Skeleton className="h-7 w-40 bg-white/5" />
            <Skeleton className="h-5 w-36 rounded-full bg-white/5" />
            <Skeleton className="h-3 w-52 bg-white/5" />
          </div>
          <div className="glass flex flex-col justify-center space-y-5 rounded-3xl p-6 sm:space-y-6 sm:p-8 lg:col-span-2">
            <Skeleton className="h-5 w-28 rounded-full bg-white/5" />
            <Skeleton className="h-9 w-3/4 bg-white/5 sm:h-10" />
            <Skeleton className="h-20 w-full bg-white/5" />
            <div className="grid grid-cols-2 gap-4 pt-2 sm:grid-cols-4 sm:pt-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="space-y-1">
                  <Skeleton className="h-3 w-16 bg-white/5" />
                  <Skeleton className="h-4 w-20 bg-white/5" />
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* 6. NarrativeCard */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-2">
              <Skeleton className="h-5 w-44 bg-white/5" />
              <Skeleton className="h-3 w-72 max-w-full bg-white/5" />
            </div>
            <Skeleton className="h-8 w-40 rounded-full bg-white/5" />
          </div>
          <div className="glass rounded-2xl p-5 sm:p-6 space-y-3">
            <Skeleton className="h-4 w-full bg-white/5" />
            <Skeleton className="h-4 w-full bg-white/5" />
            <Skeleton className="h-4 w-5/6 bg-white/5" />
            <Skeleton className="h-4 w-3/4 bg-white/5" />
          </div>
        </section>

        {/* 7. Scoring matrix */}
        <section className="space-y-6">
          <div className="flex items-center gap-4">
            <Skeleton className="h-3 w-28 bg-white/5" />
            <div className="h-px flex-1 bg-white/5" />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="glass space-y-4 rounded-xl p-6">
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-24 bg-white/5" />
                  <Skeleton className="h-4 w-4 bg-white/5" />
                </div>
                <Skeleton className="h-10 w-16 bg-white/5" />
                <Skeleton className="h-1.5 w-full bg-white/5" />
                <Skeleton className="h-4 w-full bg-white/5" />
              </div>
            ))}
          </div>
        </section>

        {/* 8. Footer */}
        <div className="pt-8 text-center sm:pt-12">
          <Skeleton className="mx-auto h-3 w-72 max-w-full bg-white/5" />
        </div>
      </main>
    </div>
  );
}
