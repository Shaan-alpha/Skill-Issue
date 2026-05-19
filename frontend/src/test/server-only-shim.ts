// Empty shim — vitest aliases the `server-only` package to this file so the
// happy-dom test env doesn't trigger server-only's client-side thrower.
// The real `server-only` package still guards production client bundles via
// Next.js's bundler — vitest just happens to not be one of those.
export {};
