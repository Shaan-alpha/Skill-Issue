import type { NextConfig } from "next";

// v0.9.5 security headers. The first four are enforced (zero-risk). CSP ships
// Report-Only: it logs violations to the browser console without blocking, so
// it can be tuned against real reports before being promoted to enforcing —
// a wrong directive would otherwise silently break PostHog/Sentry/Next.
const CSP_REPORT_ONLY = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'self'",
  "img-src 'self' data: https://avatars.githubusercontent.com",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.posthog.com https://*.i.posthog.com",
  "connect-src 'self' https://*.posthog.com https://*.i.posthog.com https://*.sentry.io https://*.ingest.sentry.io",
  "form-action 'self'",
].join("; ");

const SECURITY_HEADERS = [
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
  },
  { key: "Content-Security-Policy-Report-Only", value: CSP_REPORT_ONLY },
];

const nextConfig: NextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  // v0.8.6: enable Next 16 Cache Components for `/share/[slug]` ISR with
  // tag-based invalidation via the new `/api/revalidate` route.
  cacheComponents: true,
  experimental: {
    optimizePackageImports: ["lucide-react", "@base-ui/react"],
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "avatars.githubusercontent.com",
        pathname: "/**",
      },
    ],
  },
};

// Sentry runtime init lives in src/observability/sentry.{client,server,edge}.ts
// + instrumentation.ts. The withSentryConfig wrapper is only needed for build-
// time source-map upload + the webpack plugin's ignore-listed-frames feature,
// which fails when SENTRY_ORG / SENTRY_PROJECT aren't set. Re-add the wrapper
// in a v0.8.x patch once we provision an auth token and source-map upload.
export default nextConfig;
