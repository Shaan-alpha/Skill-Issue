import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";

export const metadata = {
  title: "404 · Skill Issue",
  description: "That route slipped through the cracks.",
};

export default function NotFound() {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center px-4 py-8 text-center sm:px-6">
      <div className="absolute inset-0 -z-10 bg-[linear-gradient(to_right,#80808005_1px,transparent_1px),linear-gradient(to_bottom,#80808005_1px,transparent_1px)] bg-[size:2rem_2rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)]" />

      <div className="glass w-full max-w-md space-y-6 rounded-3xl p-6 sm:p-10">
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground/60">
          404
        </p>
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold">Couldn&apos;t find that.</h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            The page you tried to reach isn&apos;t one we render. Could be a typo, could be a dead
            link from somewhere we used to be. Skill Issue scores GitHub usernames — try one.
          </p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-white/90"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to the landing
          </Link>
          <Link
            href="https://github.com/Shaan-alpha/Skill-Issue"
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-white/10"
          >
            <ExternalLink className="h-4 w-4" aria-hidden="true" />
            View on GitHub
          </Link>
        </div>
      </div>
    </main>
  );
}
