import type { TierName } from "@/types";

const ACCENT_BY_TIER: Record<TierName, string> = {
  Hobbyist: "#f59e0b", // amber
  "Student Builder": "#fb923c", // orange
  "Entry-Level Engineer": "#facc15", // yellow
  "Professional Developer": "#34d399", // emerald
  "Senior Engineer": "#22d3ee", // cyan
  "Staff Engineer": "#a78bfa", // violet
  "Principal Engineer": "#818cf8", // indigo
};

const FALLBACK_ACCENT = "#a3a3a3"; // neutral-400

export function tierAccent(name: TierName | string): string {
  return (ACCENT_BY_TIER as Record<string, string>)[name] ?? FALLBACK_ACCENT;
}

export const OG_BG_DARK = "#0a0a0a";
export const OG_BG_DARK_TOP = "#111111";
export const OG_FG = "#fafafa";
export const OG_FG_MUTED = "#888888";
export const OG_CREATOR_ACCENT = "#fbbf24"; // gold (amber-400) — creator card
