import Link from "next/link";
import { ArrowLeft, Building2, ExternalLink } from "lucide-react";

interface NotAnIndividualProps {
  username: string;
  detail: string;
}

// Server-rendered "this is an org, not a user" state.
// Backend returns 422 + JSON { detail: "..." } when /users/{login} resolves to
// an Organization type. We show the actual detail (so the message is consistent
// with what the API said) plus a discoverable CTA to view the org on GitHub.
export function NotAnIndividual({ username, detail }: NotAnIndividualProps) {
  const githubUrl = `https://github.com/${encodeURIComponent(username)}`;

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center px-4 py-8 text-center sm:px-6">
      <div className="absolute inset-0 -z-10 bg-[linear-gradient(to_right,#80808005_1px,transparent_1px),linear-gradient(to_bottom,#80808005_1px,transparent_1px)] bg-[size:2rem_2rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)]" />

      <div className="glass w-full max-w-md space-y-6 rounded-3xl p-6 sm:p-10">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white/5">
          <Building2 className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className="space-y-3">
          <h1 className="text-2xl font-semibold">That&apos;s an organization</h1>
          <p className="text-sm text-muted-foreground leading-relaxed">{detail}</p>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-2">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-black transition-colors hover:bg-white/90"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Try a username
          </Link>
          <a
            href={githubUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium transition-colors hover:bg-white/10"
            aria-label={`View ${username} on GitHub`}
          >
            <ExternalLink className="h-4 w-4" aria-hidden="true" />
            View on GitHub
          </a>
        </div>
      </div>
    </div>
  );
}
