export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./src/observability/sentry.server");
  }
  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./src/observability/sentry.edge");
  }
}

export async function onRequestError(
  err: unknown,
  request: { path: string; method: string; headers: Record<string, string> },
  context: { routerKind: string; routePath: string; routeType: string },
) {
  const Sentry = await import("@sentry/nextjs");
  Sentry.captureException(err, {
    extra: {
      next_request_path: request.path,
      next_request_method: request.method,
      next_router_kind: context.routerKind,
      next_route_path: context.routePath,
      next_route_type: context.routeType,
    },
  });
}
