import * as Sentry from "@sentry/nextjs";
import { APP_VERSION } from "@/lib/site";
import { SENTRY_DATA_COLLECTION, scrubEvent } from "./scrub";

const dsn = process.env.SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment:
      process.env.VERCEL_ENV ?? process.env.SENTRY_ENVIRONMENT ?? "development",
    // Ties server events to a release, as the browser's and backend's are.
    release: APP_VERSION,
    tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? 0.1),
    // The privacy contract (scrub.ts): collected at the source, then
    // scrubbed on every error and transaction.
    dataCollection: SENTRY_DATA_COLLECTION,
    beforeSend: scrubEvent,
    beforeSendTransaction: scrubEvent,
    // Replaces the Next.js init's default Http integration (same name) to
    // stop it capturing incoming request bodies; httpBodies doesn't in 10.x.
    integrations: [
      Sentry.httpIntegration({ disableIncomingRequestSpans: true, maxIncomingRequestBodySize: "none" }),
    ],
  });
}
