"use client";

import { Suspense } from "react";
import Image from "next/image";
import { Menu } from "@base-ui/react/menu";
import { useSession, signIn, signOut } from "@/lib/auth";
import { trackSignInClicked } from "@/observability/events";

function HeaderInner() {
  const session = useSession();

  if (!session) {
    return (
      <button
        type="button"
        onClick={() => { trackSignInClicked(); signIn(); }}
        className="inline-flex items-center gap-2 rounded-full border border-border bg-card/40 px-4 py-1.5 text-sm font-medium text-foreground hover:bg-card/60 transition-colors"
        aria-label="Sign in with GitHub"
      >
        Sign in with GitHub
      </button>
    );
  }

  const { login, avatar_url } = session.user;

  return (
    <Menu.Root>
      <Menu.Trigger
        className="size-9 rounded-full overflow-hidden border border-border focus-visible:outline focus-visible:outline-2 focus-visible:outline-accent"
        aria-label={`Signed in as ${login}`}
      >
        {avatar_url ? (
          <Image
            src={avatar_url}
            alt=""
            width={36}
            height={36}
            className="size-full object-cover"
          />
        ) : (
          <span className="grid place-items-center size-full text-xs">
            {login.slice(0, 2)}
          </span>
        )}
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner align="end" sideOffset={8}>
          <Menu.Popup className="min-w-[200px] rounded-lg border border-border bg-card/95 backdrop-blur-md p-1 shadow-2xl text-sm">
            <Menu.LinkItem
              href="/me"
              className="block rounded-md px-3 py-2 hover:bg-accent/10"
            >
              My analyses
            </Menu.LinkItem>
            <Menu.Item
              onClick={() => signOut().then(() => (window.location.href = "/"))}
              className="block w-full text-left rounded-md px-3 py-2 hover:bg-accent/10"
            >
              Sign out
            </Menu.Item>
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}

export function SiteHeader() {
  // min-h reserves the header's hydrated height (auth pill = 36px content,
  // plus py-3/py-4 padding) so the Suspense fallback → real-button swap
  // doesn't push `div.min-h-screen` below. Lighthouse traced the ~0.04
  // anonymous CLS to this swap.
  return (
    <header className="sticky top-0 z-30 flex items-center justify-end min-h-[3.75rem] sm:min-h-[4rem] px-4 py-3 sm:px-6 sm:py-4 bg-background/70 backdrop-blur-md border-b border-white/5">
      <Suspense fallback={<div className="h-9" aria-hidden="true" />}>
        <HeaderInner />
      </Suspense>
    </header>
  );
}
