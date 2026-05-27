import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { HistoryGrid } from "@/components/history-grid";
import type { MeAnalysesResponse } from "@/types";

// `force-dynamic` is incompatible with `cacheComponents: true` (v0.8.6).
// This page reads `cookies()` and `searchParams`, so it's auto-dynamic
// without the directive.

async function loadAnalyses(sort: string): Promise<MeAnalysesResponse> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore.getAll().map((c) => `${c.name}=${c.value}`).join("; ");
  const r = await fetch(
    `${process.env.NEXT_PUBLIC_BACKEND_URL}/me/analyses?sort=${encodeURIComponent(sort)}&page=1`,
    { headers: { cookie: cookieHeader }, cache: "no-store" },
  );
  if (r.status === 401) redirect("/");
  if (!r.ok) throw new Error("Failed to load /me/analyses");
  return r.json();
}

export default async function MePage({
  searchParams,
}: {
  searchParams: Promise<{ sort?: string }>;
}) {
  const params = await searchParams;
  const sort = params.sort ?? "recent";
  const data = await loadAnalyses(sort);

  if (data.total === 0) {
    return (
      <main className="container mx-auto max-w-3xl pt-32 pb-20 px-6">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3">
          Your engineering history
        </h1>
        <p className="text-muted-foreground mb-8">
          Analyze your first developer — saved here for later.
        </p>
        <Link
          href="/"
          className="inline-flex rounded-full bg-foreground text-background px-5 py-2 text-sm font-medium"
        >
          Go analyze
        </Link>
      </main>
    );
  }

  return (
    <main className="container mx-auto max-w-5xl pt-32 pb-20 px-4 sm:px-6">
      <header className="mb-10">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
          Your engineering history
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {data.total} {data.total === 1 ? "analysis" : "analyses"} saved
        </p>
        <nav className="mt-5 flex gap-2 text-xs">
          {(["recent", "score_desc", "score_asc"] as const).map((s) => (
            <a
              key={s}
              href={`?sort=${s}`}
              className={`rounded-full px-3 py-1 border ${
                s === sort
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {s === "recent" ? "Recent" : s === "score_desc" ? "Highest" : "Lowest"}
            </a>
          ))}
        </nav>
      </header>
      <HistoryGrid analyses={data.analyses} />
    </main>
  );
}
