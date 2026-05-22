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
    // "history_change" is the App-Router-correct value — Next.js client-side
    // navigations don't trigger a full page load, so the boolean `true` would
    // miss every next/link navigation. PostHog defaults shifted to this on
    // 2025-05-24.
    capture_pageview: "history_change",
    capture_pageleave: true,
    capture_performance: true,
    autocapture: false,
    // person_profiles defaults to "identified_only" — no need to set.
  });
  // Set eagerly so calls fired between init() and the loaded-callback don't
  // get blocked by our no-op guard — PostHog's SDK buffers pre-loaded calls
  // internally, but only if we actually forward them.
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
