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

function getServerSnapshot(): Promise<Session> {
  return Promise.resolve(null);
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
