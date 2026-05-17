"use client";

import { Suspense } from "react";
import { Menu } from "@base-ui/react/menu";
import { useSession, signIn, signOut } from "@/lib/auth";

function HeaderInner() {
  const session = useSession();

  if (!session) {
    return (
      <button
        type="button"
        onClick={signIn}
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
          // eslint-disable-next-line @next/next/no-img-element
          <img src={avatar_url} alt="" className="size-full object-cover" />
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
  return (
    <header className="absolute top-0 right-0 z-10 p-4 sm:p-6">
      <Suspense fallback={null}>
        <HeaderInner />
      </Suspense>
    </header>
  );
}
