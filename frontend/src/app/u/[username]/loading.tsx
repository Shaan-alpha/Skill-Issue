import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="min-h-screen bg-background px-4 py-6 sm:px-6 sm:py-12">
      <div className="mx-auto max-w-6xl animate-in space-y-8 sm:space-y-12">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Skeleton className="h-4 w-24 bg-white/5" />
          <div className="flex items-center gap-3">
            <Skeleton className="h-6 w-32 bg-white/5" />
            <Skeleton className="h-8 w-8 rounded-full bg-white/5" />
          </div>
        </div>

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8">
          <div className="glass flex flex-col items-center justify-center space-y-4 rounded-3xl p-6 sm:p-8 lg:col-span-1">
            <Skeleton className="h-4 w-32 bg-white/5" />
            <Skeleton className="h-36 w-36 rounded-full bg-white/5 sm:h-48 sm:w-48" />
            <Skeleton className="h-6 w-40 bg-white/5" />
          </div>
          <div className="glass flex flex-col justify-center space-y-5 rounded-3xl p-6 sm:space-y-6 sm:p-8 lg:col-span-2">
            <Skeleton className="h-6 w-24 bg-white/5" />
            <Skeleton className="h-9 w-3/4 bg-white/5 sm:h-10" />
            <Skeleton className="h-20 w-full bg-white/5" />
          </div>
        </section>

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
      </div>
    </div>
  );
}
