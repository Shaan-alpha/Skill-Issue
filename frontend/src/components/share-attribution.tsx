import { Image as ImageIcon } from "lucide-react";

export function ShareAttribution({
  login,
  avatarUrl,
  cardHref,
}: {
  login: string;
  avatarUrl: string | null;
  cardHref?: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
        {avatarUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={avatarUrl} alt="" className="size-5 rounded-full" />
        ) : null}
        <span>
          Shared by <span className="text-foreground">@{login}</span>
        </span>
      </div>
      {cardHref ? (
        <a
          href={cardHref}
          className="inline-flex items-center gap-2 rounded-full border border-border bg-card/60 px-3 py-1 text-xs font-medium hover:bg-card/80 transition-colors"
        >
          <ImageIcon className="size-3.5" aria-hidden="true" />
          Share card
        </a>
      ) : null}
    </div>
  );
}
