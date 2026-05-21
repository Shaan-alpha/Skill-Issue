"use client";

import { Popover } from "@base-ui/react/popover";
import type { Badge as BadgeT } from "@/types";
import { Badge } from "@/components/ui/badge";

interface BadgeRowProps {
  badges: BadgeT[];
}

// Each badge opens a popover with the evidence string.
// - Desktop: hover to peek (150 ms open delay, instant close) + click to pin.
// - Mobile / touch: tap toggles. Tooltip's hover-only behaviour previously
//   left mobile users with no way to read the evidence.
// - Keyboard: focus + Enter/Space toggles (Popover.Trigger renders a <button>).
export function BadgeRow({ badges }: BadgeRowProps) {
  if (badges.length === 0) return null;
  return (
    <section aria-label="Earned badges" className="flex flex-wrap gap-2">
      {badges.map((b) => (
        <Popover.Root key={b.slug}>
          <Popover.Trigger
            openOnHover
            delay={150}
            closeDelay={50}
            render={
              <Badge
                variant="outline"
                className="cursor-pointer border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent transition-colors hover:bg-accent/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                aria-label={`${b.name}: tap to read evidence`}
              >
                {b.name}
              </Badge>
            }
          />
          <Popover.Portal>
            <Popover.Positioner side="top" sideOffset={8} align="center">
              <Popover.Popup className="z-50 max-w-xs rounded-lg border border-white/10 bg-zinc-950/90 px-3 py-2 text-xs shadow-xl backdrop-blur-md">
                <Popover.Arrow className="fill-zinc-950/90 stroke-white/10" />
                <p className="font-mono text-[10px] uppercase tracking-widest text-accent">
                  {b.name}
                </p>
                <p className="mt-1 leading-relaxed text-muted-foreground">
                  {b.evidence}
                </p>
              </Popover.Popup>
            </Popover.Positioner>
          </Popover.Portal>
        </Popover.Root>
      ))}
    </section>
  );
}
