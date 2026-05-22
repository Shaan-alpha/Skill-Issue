import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
