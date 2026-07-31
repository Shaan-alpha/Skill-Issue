"use client";

import { use, useSyncExternalStore } from "react";
import type { Session } from "@/types";

const STORE_EVENT = "skill-issue:session-change";
let cachedPromise: Promise<Session> | null = null;

function backendUrl(path: string): string {
  const base = process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ?? "";
  return `${base}${path}`;
}

async function fetchSessionFresh(): Promise<Session> {
  try {
    const r = await fetch(backendUrl("/me"), {
      credentials: "include",
      cache: "no-store",
    });
    if (r.status === 401 || r.status === 404) return null;
    if (!r.ok) return null;
    const body = await r.json();
    return { user: body.user };
  } catch {
    return null;
  }
}

function getCachedPromise(): Promise<Session> {
  if (cachedPromise === null) cachedPromise = fetchSessionFresh();
  return cachedPromise;
}

function invalidate() {
  cachedPromise = null;
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(STORE_EVENT));
  }
}

function subscribe(cb: () => void) {
  if (typeof window === "undefined") return () => {};
  window.addEventListener(STORE_EVENT, cb);
  return () => window.removeEventListener(STORE_EVENT, cb);
}

function getSnapshot(): Promise<Session> {
  return getCachedPromise();
}

// Must be a stable reference. `useSyncExternalStore` compares snapshots with
// Object.is, and `use()` needs a promise identity it can resolve against a
// cache — returning `Promise.resolve(null)` from the function body minted a new
// promise on every call, which is what produced both of the console errors this
// app had learned to treat as background noise:
//   "The result of getServerSnapshot should be cached to avoid an infinite loop"
//   "A component was suspended by an uncached promise"
// React's own wording ("to avoid an infinite loop") is the tell that this was
// never cosmetic. There is no server session to report — the cookie is read by
// the browser — so a single resolved-null promise is the correct snapshot.
const SERVER_SNAPSHOT: Promise<Session> = Promise.resolve(null);

function getServerSnapshot(): Promise<Session> {
  return SERVER_SNAPSHOT;
}

export function useSession(): Session {
  const promise = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  return use(promise);
}

export async function signOut(): Promise<void> {
  await fetch(backendUrl("/auth/logout"), {
    method: "POST",
    credentials: "include",
  });
  invalidate();
}

export function signIn(): void {
  if (typeof window !== "undefined") {
    window.location.href = backendUrl("/auth/login");
  }
}
