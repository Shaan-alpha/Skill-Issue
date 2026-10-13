import * as Sentry from "@sentry/nextjs";
import { APP_VERSION } from "@/lib/site";
import { scrubEvent } from "./scrub";

const dsn = process.env.SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment:
      process.env.VERCEL_ENV ?? process.env.SENTRY_ENVIRONMENT ?? "development",
    // Ties server events to a release, as the browser's and backend's are.
    release: APP_VERSION,
    tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? 0.1),
    sendDefaultPii: false,
    beforeSend: scrubEvent,
  });
}
