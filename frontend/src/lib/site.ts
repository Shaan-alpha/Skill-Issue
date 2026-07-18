// Single source of truth for the app version surfaced in the UI.
// Bump alongside package.json on each release so the hero badge and the
// results footer never drift apart.
export const APP_VERSION = "1.0.3";

// Canonical site origin. Prod sets NEXT_PUBLIC_SITE_URL; the fallback is the
// production domain so metadata/OG URLs never point at a preview host.
export function siteOrigin(): string {
  const fromEnv = process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  return "https://skillissue.tech";
}

export function siteHost(): string {
  return siteOrigin().replace(/^https?:\/\//, "");
}
