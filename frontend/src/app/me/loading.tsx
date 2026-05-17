export default function Loading() {
  return (
    <main className="container mx-auto max-w-5xl pt-32 pb-20 px-4 sm:px-6">
      <div className="h-10 w-72 rounded-md bg-card/40 animate-pulse mb-10" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-40 rounded-2xl border border-border bg-card/40 animate-pulse" />
        ))}
      </div>
    </main>
  );
}
