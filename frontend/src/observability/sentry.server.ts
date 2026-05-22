import * as Sentry from "@sentry/nextjs";

const SCRUB_HEADER_NAMES = new Set(["cookie", "set-cookie", "authorization"]);
const SCRUB_EXTRA_KEYS = new Set([
  "access_token",
  "access_token_ct",
  "oauth_state",
  "oauth_code",
  "session_id",
  "email",
]);

function scrubHeaders(headers: Record<string, string> | undefined) {
  if (!headers) return headers;
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(headers)) {
    if (!SCRUB_HEADER_NAMES.has(k.toLowerCase())) out[k] = v;
  }
  return out;
}

function scrubObject<T>(value: T): T {
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(scrubObject) as unknown as T;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (SCRUB_EXTRA_KEYS.has(k)) continue;
    out[k] = scrubObject(v);
  }
  return out as unknown as T;
}

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
