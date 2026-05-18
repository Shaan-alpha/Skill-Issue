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
  return (
    <div
      role="radiogroup"
      aria-label="Narrative Mode"
      className={cn(
        "inline-flex items-center rounded-full bg-white/5 p-1 backdrop-blur border border-white/10",
        disabled && "opacity-50 pointer-events-none"
      )}
    >
      <button
        role="radio"
        aria-checked={mode === "roast"}
        onClick={() => onModeChange("roast")}
        className={cn(
          "relative flex items-center justify-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium transition-colors z-10 min-w-[7.5rem]",
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
          "relative flex items-center justify-center gap-2 rounded-full px-4 py-1.5 text-xs font-medium transition-colors z-10 min-w-[7.5rem]",
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
