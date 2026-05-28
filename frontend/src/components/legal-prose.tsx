import type { ReactNode } from "react";

export function LegalProse({
  title,
  lastUpdated,
  children,
}: {
  title: string;
  lastUpdated: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">Last updated {lastUpdated}</p>
      <div className="mt-8 space-y-8 text-sm leading-relaxed text-muted-foreground sm:text-base">
        {children}
      </div>
    </div>
  );
}

export function LegalSection({ heading, children }: { heading: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-foreground sm:text-xl">{heading}</h2>
      {children}
    </section>
  );
}
