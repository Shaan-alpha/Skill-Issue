import * as Sentry from "@sentry/nextjs";
import { scrubHeaders, scrubObject } from "./scrub";

const dsn = process.env.SENTRY_DSN;

if (dsn) {
  Sentry.init({
    dsn,
    environment:
      process.env.VERCEL_ENV ?? process.env.SENTRY_ENVIRONMENT ?? "development",
    tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? 0.1),
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
