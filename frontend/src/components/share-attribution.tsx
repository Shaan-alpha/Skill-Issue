export function ShareAttribution({ login, avatarUrl }: { login: string; avatarUrl: string | null }) {
  return (
    <div className="inline-flex items-center gap-2 text-xs text-muted-foreground">
      {avatarUrl ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={avatarUrl} alt="" className="size-5 rounded-full" />
      ) : null}
      <span>
        Shared by <span className="text-foreground">@{login}</span>
      </span>
    </div>
  );
}
