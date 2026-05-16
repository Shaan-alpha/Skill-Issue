"use client";

import { useState } from "react";
import { NarrativeMode } from "@/types";
import { ModePillToggle } from "./mode-pill-toggle";
import { NarrativeStream } from "./narrative-stream";

interface NarrativeCardProps {
  username: string;
}

export function NarrativeCard({ username }: NarrativeCardProps) {
  const [mode, setMode] = useState<NarrativeMode>("roast");

  return (
    <section className="space-y-4" aria-label="AI Narrative Analysis">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
            <span>Executive Overview</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-accent/20 text-accent font-mono font-normal">
              AI
            </span>
          </h2>
          <p className="text-xs text-muted-foreground">
            Real-time synthesized breakdown of your engineering footprint.
          </p>
        </div>

        <ModePillToggle mode={mode} onModeChange={setMode} />
      </div>

      <NarrativeStream username={username} mode={mode} />
    </section>
  );
}
