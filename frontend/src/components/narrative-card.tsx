"use client";

import { useSyncExternalStore } from "react";
import { NarrativeMode } from "@/types";
import { ModePillToggle } from "./mode-pill-toggle";
import { NarrativeStream } from "./narrative-stream";

const STORAGE_KEY = "skill_issue_narrative_mode";
const MODE_CHANGE_EVENT = "skill-issue:narrative-mode-change";

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(MODE_CHANGE_EVENT, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(MODE_CHANGE_EVENT, callback);
  };
}

function getSnapshot(): NarrativeMode {
  const saved = localStorage.getItem(STORAGE_KEY);
  return saved === "mentor" ? "mentor" : "roast";
}

function getServerSnapshot(): NarrativeMode {
  return "roast";
}

function useNarrativeMode(): [NarrativeMode, (next: NarrativeMode) => void] {
  const mode = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const setMode = (next: NarrativeMode) => {
    localStorage.setItem(STORAGE_KEY, next);
    window.dispatchEvent(new Event(MODE_CHANGE_EVENT));
  };
  return [mode, setMode];
}

interface NarrativeCardProps {
  username: string;
}

export function NarrativeCard({ username }: NarrativeCardProps) {
  const [mode, setMode] = useNarrativeMode();

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

      <NarrativeStream key={`${username}-${mode}`} username={username} mode={mode} />
    </section>
  );
}
