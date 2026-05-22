import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

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

export default withSentryConfig(nextConfig, {
  silent: true,
  // hideSourceMaps was removed in v10; use sourcemaps.disable instead
  sourcemaps: {
    disable: true,
  },
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
});
