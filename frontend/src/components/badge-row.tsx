"use client";

import { Tooltip } from "@base-ui/react/tooltip";
import type { Badge as BadgeT } from "@/types";
import { Badge } from "@/components/ui/badge";

interface BadgeRowProps {
  badges: BadgeT[];
}

export function BadgeRow({ badges }: BadgeRowProps) {
  if (badges.length === 0) return null;
  return (
    <section aria-label="Earned badges" className="flex flex-wrap gap-2">
      <Tooltip.Provider delay={150}>
        {badges.map((b) => (
          <Tooltip.Root key={b.slug}>
            <Tooltip.Trigger
              render={
                <Badge
                  variant="outline"
                  className="cursor-help border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent transition-colors hover:bg-accent/15"
                >
                  {b.name}
                </Badge>
              }
            />
            <Tooltip.Portal>
              <Tooltip.Positioner side="top" sideOffset={8} align="center">
                <Tooltip.Popup className="z-50 max-w-xs rounded-lg border border-white/10 bg-zinc-950/90 px-3 py-2 text-xs shadow-xl backdrop-blur-md">
                  <Tooltip.Arrow className="fill-zinc-950/90 stroke-white/10" />
                  <p className="font-mono text-[10px] uppercase tracking-widest text-accent">
                    {b.name}
                  </p>
                  <p className="mt-1 leading-relaxed text-muted-foreground">
                    {b.evidence}
                  </p>
                </Tooltip.Popup>
              </Tooltip.Positioner>
            </Tooltip.Portal>
          </Tooltip.Root>
        ))}
      </Tooltip.Provider>
    </section>
  );
}
