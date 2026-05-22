/**
 * Shared PII scrubbing helpers for Sentry's beforeSend hook.
 *
 * Must stay in sync with the backend's _SCRUB_HEADER_NAMES + _SCRUB_EXTRA_KEYS
 * in app/observability/sentry.py. PII contract lives in v0.8.0 design spec §6.
 */

export const SCRUB_HEADER_NAMES = new Set([
  "cookie",
  "set-cookie",
  "authorization",
  "x-vercel-id",
]);

export const SCRUB_EXTRA_KEYS = new Set([
  "access_token",
  "access_token_ct",
  "oauth_state",
  "oauth_code",
  "session_id",
  "email",
]);

export function scrubHeaders(headers: Record<string, string> | undefined) {
  if (!headers) return headers;
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(headers)) {
    if (!SCRUB_HEADER_NAMES.has(k.toLowerCase())) out[k] = v;
  }
  return out;
}

export function scrubObject<T>(value: T): T {
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(scrubObject) as unknown as T;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
    if (SCRUB_EXTRA_KEYS.has(k)) continue;
    out[k] = scrubObject(v);
  }
  return out as unknown as T;
}
