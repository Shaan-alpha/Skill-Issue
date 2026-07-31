"use client";

import { useLayoutEffect, useRef, useState } from "react";
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
// - Keyboard: focus + Enter/Space toggles.
//
// `nativeButton={false}` is load-bearing, not decoration. The trigger renders
// through `Badge`, which is a <span>, and Base UI defaults `nativeButton` to
// true — so it emitted `type="button"` on a span and left the element with no
// role at all. Screen readers announced an unlabelled span rather than a
// button. Told the truth, Base UI applies `role="button"` and the non-native
// keyboard handling instead. Base UI warns about this at runtime; the warning
// was being swallowed in test output.
// Controlled rather than uncontrolled purely so the popup can be forced shut
// when the route is hidden. `Popover.Portal` mounts the popup into
// document.body — *outside* the <Activity> boundary — so the boundary's
// `display: none` never reaches it, and a popover left pinned open when the
// user hits browser-back would stay painted over the next route. React runs
// layout-effect cleanups on the hide→show transition just as it does on
// unmount, which is the reset hook the Next docs point at for transient
// open/closed state. State stays per badge so hover and pin behave exactly as
// they did before.
function BadgeChip({ badge }: { badge: BadgeT }) {
  const [open, setOpen] = useState(false);
  const positionerRef = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    return () => {
      // Order matters. `setOpen(false)` alone is what the Next guide prescribes
      // for transient open/closed state, and it is not enough here: the update
      // is scheduled against a subtree React has just hidden, and hidden
      // Activity content re-renders at low priority — verified, the cleanup
      // runs but `data-open` is still on the popup afterwards. Since the popup
      // is portaled outside the boundary, nothing hides it in the meantime, so
      // drop it out of the layout synchronously first. The state update still
      // matters: it leaves the chip logically closed for the re-show.
      // Reading the ref in the cleanup is the point, not an oversight: the
      // popup does not exist when the effect body runs (it is only rendered
      // while open), so the usual "copy ref.current into a variable" advice
      // would capture null and hide nothing.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      positionerRef.current?.style.setProperty("display", "none");
      setOpen(false);
    };
  }, []);

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger
        nativeButton={false}
        openOnHover
        delay={150}
        closeDelay={50}
        render={
          <Badge
            variant="outline"
            className="cursor-pointer border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent transition-colors hover:bg-accent/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            aria-label={`${badge.name}: tap to read evidence`}
          >
            {badge.name}
          </Badge>
        }
      />
      <Popover.Portal>
        <Popover.Positioner ref={positionerRef} side="top" sideOffset={8} align="center">
          <Popover.Popup className="z-50 max-w-xs rounded-lg border border-white/10 bg-zinc-950/90 px-3 py-2 text-xs shadow-xl backdrop-blur-md">
            <Popover.Arrow className="fill-zinc-950/90 stroke-white/10" />
            <p className="font-mono text-[10px] uppercase tracking-widest text-accent">
              {badge.name}
            </p>
            <p className="mt-1 leading-relaxed text-muted-foreground">
              {badge.evidence}
            </p>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}

export function BadgeRow({ badges }: BadgeRowProps) {
  if (badges.length === 0) return null;
  return (
    <section aria-label="Earned badges" className="flex flex-wrap gap-2">
      {badges.map((b) => (
        <BadgeChip key={b.slug} badge={b} />
      ))}
    </section>
  );
}
