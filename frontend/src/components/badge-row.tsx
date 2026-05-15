import type { Badge as BadgeT } from "@/types";
import { Badge } from "@/components/ui/badge";

interface BadgeRowProps {
  badges: BadgeT[];
}

export function BadgeRow({ badges }: BadgeRowProps) {
  if (badges.length === 0) return null;
  return (
    <section
      aria-label="Earned badges"
      className="flex flex-wrap gap-2"
    >
      {badges.map((b) => (
        <Badge
          key={b.slug}
          variant="outline"
          className="border-accent/20 bg-accent/10 text-accent"
          title={b.evidence}
        >
          {b.name}
        </Badge>
      ))}
    </section>
  );
}
