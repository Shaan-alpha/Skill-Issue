"use client";

import { NarrativeMode } from "@/types";
import { m } from "framer-motion";
import { Compass, Flame } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModePillToggleProps {
  mode: NarrativeMode;
  onModeChange: (mode: NarrativeMode) => void;
  disabled?: boolean;
}

export function ModePillToggle({
  mode,
  onModeChange,
  disabled,
}: ModePillToggleProps) {
  // Container is `flex w-full sm:inline-flex sm:w-auto`:
  //   - Mobile (flex-col parent → align-items:stretch → toggle gets full row
  //     width). We embrace it and let the buttons split it 50/50 via `flex-1`,
  //     so the two pills are perfectly symmetric.
  //   - Desktop (flex-row parent → toggle sizes to content). Buttons stop
  //     stretching and fall back to a fixed `min-w-[7.5rem]` so the toggle
  //     keeps its natural compact look next to the heading.
  return (
    <div
      role="radiogroup"
      aria-label="Narrative Mode"
      className={cn(
        "flex w-full items-center rounded-full bg-white/5 p-1 backdrop-blur border border-white/10 sm:inline-flex sm:w-auto",
        disabled && "opacity-50 pointer-events-none"
      )}
    >
      <button
        role="radio"
        aria-checked={mode === "roast"}
        onClick={() => onModeChange("roast")}
        className={cn(
          "relative flex flex-1 items-center justify-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium transition-colors z-10 sm:flex-none sm:min-w-[7.5rem]",
          mode === "roast"
            ? "text-white"
            : "text-muted-foreground hover:text-white"
        )}
      >
        {mode === "roast" && (
          <m.div
            layoutId="pill-active-bg"
            className="absolute inset-0 rounded-full bg-red-500/20 border border-red-500/30 -z-10"
            transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
          />
        )}
        <Flame
          className={cn("w-3.5 h-3.5", mode === "roast" && "text-red-400")}
        />
        <span>Roast Mode</span>
      </button>

      <button
        role="radio"
        aria-checked={mode === "mentor"}
        onClick={() => onModeChange("mentor")}
        className={cn(
          "relative flex flex-1 items-center justify-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium transition-colors z-10 sm:flex-none sm:min-w-[7.5rem]",
          mode === "mentor"
            ? "text-white"
            : "text-muted-foreground hover:text-white"
        )}
      >
        {mode === "mentor" && (
          <m.div
            layoutId="pill-active-bg"
            className="absolute inset-0 rounded-full bg-blue-500/20 border border-blue-500/30 -z-10"
            transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
          />
        )}
        <Compass
          className={cn("w-3.5 h-3.5", mode === "mentor" && "text-blue-400")}
        />
        <span>Mentor Mode</span>
      </button>
    </div>
  );
}
