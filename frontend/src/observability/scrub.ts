import type * as Sentry from "@sentry/nextjs";

/**
 * The Sentry privacy contract (docs/OBSERVABILITY.md, "PII contract"),
 * shared by the browser, server and edge inits.
 *
 * The backend mirrors these lists in app/observability/sentry.py, and
 * backend/tests/observability/test_scrub_drift.py fails if they diverge.
 * Keep each list a flat array of string literals so that test can parse it.
 */

// Request headers that may reach Sentry; every other header is dropped.
export const HEADER_ALLOWLIST = ["user-agent", "referer", "content-type", "accept", "host"];

// A query parameter whose name contains one of these keeps its name, and its
// value becomes [Filtered]: OAuth code and state, tokens, keys, sessions.
export const QUERY_DENY_TERMS = [
  "code",
  "state",
  "token",
  "key",
  "secret",
  "session",
  "sid",
  "passw",
  "pwd",
  "credential",
  "csrf",
  "xsrf",
  "jwt",
  "bearer",
];

// Keys removed from `extra` and `contexts` wherever they appear.
export const SCRUB_EXTRA_KEYS = [
  "access_token",
  "access_token_ct",
  "oauth_state",
  "oauth_code",
  "session_id",
  "email",
];

export const FILTERED = "[Filtered]";

// Not re-exported by @sentry/nextjs, so read it off init's options.
type DataCollection = NonNullable<Parameters<typeof Sentry.init>[0]["dataCollection"]>;

/**
 * What the SDK collects at the source, in every runtime. It replaces
 * sendDefaultPii, whose `false` still let RequestData attach raw cookies.
 * It also governs the request headers 10.x copies onto server spans.
 */
export const SENTRY_DATA_COLLECTION: DataCollection = {
  userInfo: false,
  cookies: false,
  httpHeaders: {
    request: { allow: HEADER_ALLOWLIST },
    response: { allow: HEADER_ALLOWLIST },
  },
  httpBodies: [],
  urlQueryParams: { deny: QUERY_DENY_TERMS },
  graphQL: { document: false, variables: false },
  genAI: { inputs: false, outputs: false },
  databaseQueryData: false,
  stackFrameVariables: false,
};

type Bag = Record<string, unknown>;

const ALLOWED_HEADERS = new Set(HEADER_ALLOWLIST);
const EXTRA_KEYS = new Set(SCRUB_EXTRA_KEYS);
// Span attributes carry headers as http.request.header.user_agent and so on.
const ALLOWED_SPAN_HEADER_KEYS = new Set(
  ["request", "response"].flatMap((direction) =>
    HEADER_ALLOWLIST.map((name) => `http.${direction}.header.${name.replace(/-/g, "_")}`),
  ),
);
const URL_DATA_KEYS = new Set(["http.target", "http.url", "url.full", "url"]);
const QUERY_DATA_KEYS = new Set(["url.query", "http.query"]);

function isBag(value: unknown): value is Bag {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isSensitiveParam(name: string): boolean {
  const lower = name.toLowerCase();
  return QUERY_DENY_TERMS.some((term) => lower.includes(term));
}

/**
 * Blanks the values of sensitive parameters. A plain split, never URL
 * encoding, so the result matches the backend's byte for byte.
 */
export function filterQuery(query: string): string {
  const prefix = query.startsWith("?") ? "?" : "";
  const pairs = query
    .slice(prefix.length)
    .split("&")
    .map((pair) => {
      const eq = pair.indexOf("=");
      return eq !== -1 && isSensitiveParam(pair.slice(0, eq)) ? `${pair.slice(0, eq)}=${FILTERED}` : pair;
    });
  return prefix + pairs.join("&");
}

/** Filters the query part of a URL or path; the rest is untouched. */
export function filterUrl(url: string): string {
  const q = url.indexOf("?");
  if (q === -1) return url;
  const hash = url.indexOf("#", q);
  const end = hash === -1 ? url.length : hash;
  return `${url.slice(0, q + 1)}${filterQuery(url.slice(q + 1, end))}${url.slice(end)}`;
}

/**
 * Replaces owner[key] with its scrubbed value, or drops it if scrubbing
 * throws. Fails closed: a part we can't read is a part we don't send. The
 * hook itself must never throw, because the SDK would drop the whole event.
 */
function replace(owner: Bag, key: string, scrub: (value: unknown) => unknown): void {
  if (!(key in owner)) return;
  try {
    owner[key] = scrub(owner[key]);
  } catch {
    delete owner[key];
  }
}

function allowedHeaders(headers: unknown): Bag {
  if (!isBag(headers)) throw new TypeError("request headers");
  const out: Bag = {};
  for (const [name, value] of Object.entries(headers)) {
    const lower = name.toLowerCase();
    if (!ALLOWED_HEADERS.has(lower)) continue;
    out[name] = lower === "referer" && typeof value === "string" ? filterUrl(value) : value;
  }
  return out;
}

function filteredQueryString(value: unknown): unknown {
  if (typeof value === "string") return filterQuery(value);
  if (Array.isArray(value)) {
    return value.map((pair) =>
      Array.isArray(pair) && pair.length === 2 && typeof pair[0] === "string" && isSensitiveParam(pair[0])
        ? [pair[0], FILTERED]
        : pair,
    );
  }
  if (isBag(value)) {
    return Object.fromEntries(
      Object.entries(value).map(([name, v]) => [name, isSensitiveParam(name) ? FILTERED : v]),
    );
  }
  throw new TypeError("query_string");
}

function filteredUrlValue(value: unknown): string {
  if (typeof value !== "string") throw new TypeError("url");
  return filterUrl(value);
}

function scrubRequest(request: unknown): Bag {
  if (!isBag(request)) throw new TypeError("request");
  delete request.cookies;
  delete request.data;
  delete request.env;
  replace(request, "headers", allowedHeaders);
  replace(request, "query_string", filteredQueryString);
  replace(request, "url", filteredUrlValue);
  return request;
}

function scrubUser(user: unknown): Bag {
  if (!isBag(user)) throw new TypeError("user");
  delete user.ip_address;
  delete user.email;
  return user;
}

function scrubbedSpanData(data: unknown): Bag {
  if (!isBag(data)) throw new TypeError("span data");
  const out: Bag = {};
  for (const [key, value] of Object.entries(data)) {
    if (key.startsWith("http.request.header.") || key.startsWith("http.response.header.")) {
      if (ALLOWED_SPAN_HEADER_KEYS.has(key)) {
        out[key] = key.endsWith(".referer") && typeof value === "string" ? filterUrl(value) : value;
      }
    } else if (key === "http.request.body.data") {
      continue;
    } else if (URL_DATA_KEYS.has(key) && typeof value === "string") {
      out[key] = filterUrl(value);
    } else if (QUERY_DATA_KEYS.has(key) && typeof value === "string") {
      out[key] = filterQuery(value);
    } else {
      out[key] = value;
    }
  }
  return out;
}

export function scrubObject<T>(value: T): T {
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(scrubObject) as unknown as T;
  const out: Bag = {};
  for (const [k, v] of Object.entries(value as Bag)) {
    if (EXTRA_KEYS.has(k)) continue;
    out[k] = scrubObject(v);
  }
  return out as unknown as T;
}

function scrubContexts(contexts: unknown): Bag {
  if (!isBag(contexts)) throw new TypeError("contexts");
  if (isBag(contexts.trace)) replace(contexts.trace, "data", scrubbedSpanData);
  if (isBag(contexts.nextjs)) replace(contexts.nextjs, "request_path", filteredUrlValue);
  return scrubObject(contexts);
}

function scrubSpans(spans: unknown): unknown[] {
  if (!Array.isArray(spans)) throw new TypeError("spans");
  for (const span of spans) if (isBag(span)) replace(span, "data", scrubbedSpanData);
  return spans;
}

function scrubbedBreadcrumbData(data: unknown): Bag {
  if (!isBag(data)) throw new TypeError("breadcrumb data");
  for (const key of ["url", "from", "to"]) {
    const value = data[key];
    if (typeof value === "string") data[key] = filterUrl(value);
  }
  return data;
}

function scrubBreadcrumbs(breadcrumbs: unknown): unknown[] {
  if (!Array.isArray(breadcrumbs)) throw new TypeError("breadcrumbs");
  for (const crumb of breadcrumbs) if (isBag(crumb)) replace(crumb, "data", scrubbedBreadcrumbData);
  return breadcrumbs;
}

/**
 * `beforeSend` and `beforeSendTransaction` for every runtime: enforces the
 * PII contract on errors and transactions alike.
 */
export function scrubEvent<T extends Sentry.Event>(event: T): T {
  const bag = event as unknown as Bag;
  replace(bag, "request", scrubRequest);
  replace(bag, "user", scrubUser);
  replace(bag, "contexts", scrubContexts);
  replace(bag, "spans", scrubSpans);
  replace(bag, "breadcrumbs", scrubBreadcrumbs);
  replace(bag, "extra", scrubObject);
  return event;
}
