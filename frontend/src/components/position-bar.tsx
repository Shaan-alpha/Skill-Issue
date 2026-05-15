"use client";

import { m } from "framer-motion";
import type { TierInfo } from "@/types";

const TIER_ABBREV: Record<string, string> = {
  Hobbyist: "Hob",
  "Student Builder": "Stu",
  "Entry-Level Engineer": "Entry",
  "Professional Developer": "Pro",
  "Senior Engineer": "Senior",
  "Staff Engineer": "Staff",
  "Principal Engineer": "Principal",
};

// Tier band lower bounds for visual dividers — kept in sync with backend `tiers.py`.
const DIVIDERS = [20, 35, 50, 65, 80, 90];

interface PositionBarProps {
  tier: TierInfo;
  total: number;
}

export function PositionBar({ tier, total }: PositionBarProps) {
  const pct = Math.max(0, Math.min(100, total));
  const captionBelow =
    tier.pts_to_next === null || tier.next_tier === null
      ? "Top tier · no further band"
      : `${tier.pts_to_next} pts to ${tier.next_tier}`;

  return (
    <section
      aria-label={`${tier.name} · ${tier.sub_rank} of 100`}
      className="glass space-y-3 rounded-2xl p-4 sm:p-6"
    >
      <div className="flex items-baseline justify-between text-sm">
        <span className="font-semibold">
          {tier.name}
          <span className="text-muted-foreground"> · {tier.sub_rank}/100</span>
        </span>
        <span className="text-xs text-muted-foreground">{captionBelow}</span>
      </div>
      <div
        className="relative h-2 w-full overflow-hidden rounded-full bg-white/5"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={total}
        aria-label={`${tier.name} · ${tier.sub_rank} of 100`}
      >
        {DIVIDERS.map((d) => (
          <span
            key={d}
            aria-hidden="true"
            className="absolute top-0 h-full w-px bg-white/10"
            style={{ left: `${d}%` }}
          />
        ))}
        <m.span
          aria-hidden="true"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
          className="absolute left-0 top-0 h-full rounded-full bg-accent"
        />
      </div>
      <div className="flex justify-between text-[11px] uppercase tracking-widest text-muted-foreground">
        {Object.keys(TIER_ABBREV).map((name) => (
          <span
            key={name}
            className={name === tier.name ? "text-foreground" : ""}
          >
            {TIER_ABBREV[name]}
          </span>
        ))}
      </div>
    </section>
  );
}
