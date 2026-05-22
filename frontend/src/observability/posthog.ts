"use client";

import posthog from "posthog-js";

let initialised = false;

export function initPostHog(): void {
  if (initialised) return;
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key) return;
  const host = process.env.NEXT_PUBLIC_POSTHOG_HOST ?? "https://us.i.posthog.com";
  posthog.init(key, {
    api_host: host,
    capture_pageview: true,
    capture_pageleave: true,
    capture_performance: true,
    autocapture: false,
    person_profiles: "identified_only",
    loaded: () => {
      initialised = true;
    },
  });
  initialised = true;
}

export function identifyPostHog(distinctId: string): void {
  if (!initialised) return;
  posthog.identify(distinctId);
}

export function resetPostHog(): void {
  if (!initialised) return;
  posthog.reset();
}

/**
 * @internal Implementation backbone for the typed helpers in `events.ts`.
 * Callers should use the typed helpers (trackAnalyzeSubmitted, etc.) — they
 * enforce the event-name + payload contract. Don't call this directly.
 */
export function track(
  event: string,
  properties: Record<string, unknown> = {},
): void {
  if (!initialised) return;
  posthog.capture(event, properties);
}
