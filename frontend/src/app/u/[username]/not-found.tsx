import Link from "next/link";
import { ArrowLeft, UserX } from "lucide-react";

export default function UserNotFound() {
  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center px-4 py-8 text-center sm:px-6">
      <div className="absolute inset-0 -z-10 bg-[linear-gradient(to_right,#80808005_1px,transparent_1px),linear-gradient(to_bottom,#80808005_1px,transparent_1px)] bg-[size:2rem_2rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)]" />

      <div className="glass w-full max-w-md space-y-6 rounded-3xl p-6 sm:p-10">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white/5">
          <UserX className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
        </div>
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold">No such GitHub user</h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            We checked GitHub and that username doesn&apos;t exist. Double-check the spelling —
            usernames are case-insensitive but every other character matters.
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-white/10"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Try another username
        </Link>
      </div>
    </main>
  );
}
