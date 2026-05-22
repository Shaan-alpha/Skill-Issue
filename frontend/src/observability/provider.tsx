"use client";

import { Suspense, useEffect } from "react";
import { useSession } from "@/lib/auth";
import { identifyPostHog, initPostHog, resetPostHog } from "./posthog";

function SessionIdentifier() {
  const session = useSession();

  useEffect(() => {
    if (session?.user?.id) {
      identifyPostHog(String(session.user.id));
    } else {
      resetPostHog();
    }
  }, [session?.user?.id]);

  return null;
}

export function ObservabilityProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    initPostHog();
  }, []);

  return (
    <>
      <Suspense>
        <SessionIdentifier />
      </Suspense>
      {children}
    </>
  );
}
