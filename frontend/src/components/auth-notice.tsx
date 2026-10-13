"use client";

import { useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

// The OAuth callback sends people back to the site with `?auth=<outcome>`
// instead of a raw error page. Only these values are shown; anything else in
// the parameter is ignored.
const MESSAGES = {
  failed: "Sign-in didn't complete. Please try again.",
  cancelled: "Sign-in was cancelled.",
} as const;

type Outcome = keyof typeof MESSAGES;

function isOutcome(value: string | null): value is Outcome {
  return value === "failed" || value === "cancelled";
}

export function AuthNotice() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const [dismissed, setDismissed] = useState(false);

  const outcome = params.get("auth");
  if (dismissed || !isOutcome(outcome)) return null;

  return (
    <div
      role="status"
      className="fixed inset-x-4 bottom-6 z-50 mx-auto flex max-w-md items-center justify-between gap-3 rounded-2xl border border-border bg-card/90 px-4 py-1 text-sm shadow-lg backdrop-blur"
    >
      <span className="text-muted-foreground">{MESSAGES[outcome]}</span>
      <button
        type="button"
        onClick={() => {
          setDismissed(true);
          router.replace(pathname, { scroll: false });
        }}
        className="min-h-11 shrink-0 px-2 font-medium text-accent hover:underline"
      >
        Dismiss
      </button>
    </div>
  );
}
