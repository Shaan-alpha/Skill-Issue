import * as Sentry from "@sentry/nextjs";

export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./src/observability/sentry.server");
  }
  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./src/observability/sentry.edge");
  }
}

// Sentry's purpose-built handler for Next 16's onRequestError hook — captures
// the error + full request + full context (renderSource, revalidateReason,
// renderType — fields our previous hand-roll dropped on the floor).
export const onRequestError = Sentry.captureRequestError;
