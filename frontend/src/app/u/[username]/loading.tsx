import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="min-h-screen bg-background py-12 px-6">
      <div className="max-w-6xl mx-auto space-y-12 animate-in">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24 bg-white/5" />
          <div className="flex items-center gap-4">
            <Skeleton className="h-6 w-32 bg-white/5" />
            <Skeleton className="h-8 w-8 rounded-full bg-white/5" />
          </div>
        </div>

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1 glass p-8 rounded-3xl flex flex-col items-center justify-center space-y-4">
            <Skeleton className="h-4 w-32 bg-white/5" />
            <Skeleton className="h-48 w-48 rounded-full bg-white/5" />
            <Skeleton className="h-6 w-40 bg-white/5" />
          </div>
          <div className="lg:col-span-2 glass p-8 rounded-3xl flex flex-col justify-center space-y-6">
            <Skeleton className="h-6 w-24 bg-white/5" />
            <Skeleton className="h-10 w-full bg-white/5" />
            <Skeleton className="h-20 w-full bg-white/5" />
          </div>
        </section>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="glass p-6 rounded-xl space-y-4">
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
