// Next loads this file in the browser before the app becomes interactive
// (instrumentation-client convention) — it is the ONLY thing that pulls the
// Sentry client init into the bundle. Without it, sentry.client.ts is an
// orphaned module and frontend Sentry silently never runs (v0.8.0–v1.0.0 bug).
import * as Sentry from "@sentry/nextjs";

import "./src/observability/sentry.client";

// Navigation instrumentation for App Router transitions (pairs with
// onRequestError in instrumentation.ts).
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
