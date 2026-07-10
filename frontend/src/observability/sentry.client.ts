"use client";

import * as Sentry from "@sentry/nextjs";
import { scrubHeaders, scrubObject } from "./scrub";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment:
      process.env.NEXT_PUBLIC_VERCEL_ENV ??
      process.env.SENTRY_ENVIRONMENT ??
      "development",
    // `||` not `??`: a present-but-blank env var must fall back to the
    // default, not become Number("") === 0 and silently disable sampling.
    // An explicit "0" stays honored ("0" is a truthy string).
    tracesSampleRate: Number(
      process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE || 0.2,
    ),
    // Session Replay (Sentry education plan). Masking stays default-on —
    // the v0.8.0 PII contract applies to replay payloads too.
    integrations: [Sentry.replayIntegration()],
    replaysSessionSampleRate: Number(
      process.env.NEXT_PUBLIC_SENTRY_REPLAYS_SESSION_SAMPLE_RATE || 0.1,
    ),
    replaysOnErrorSampleRate: Number(
      process.env.NEXT_PUBLIC_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE || 1.0,
    ),
    sendDefaultPii: false,
    beforeSend(event) {
      if (event.request) {
        event.request.headers = scrubHeaders(
          event.request.headers as Record<string, string> | undefined,
        );
      }
      if (event.user && "email" in event.user) {
        delete (event.user as { email?: string }).email;
      }
      if (event.extra) event.extra = scrubObject(event.extra);
      if (event.contexts) event.contexts = scrubObject(event.contexts);
      return event;
    },
  });
}
