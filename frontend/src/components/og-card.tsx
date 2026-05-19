import type { Report } from "@/types";
import {
  OG_BG_DARK,
  OG_BG_DARK_TOP,
  OG_FG,
  OG_FG_MUTED,
  tierAccent,
} from "@/lib/og-palette";

interface Props {
  report: Report;
  /** Optional avatar URL — passed by route handlers when known. */
  avatarUrl?: string | null;
}

/**
 * Pure JSX used by `next/og`'s `ImageResponse`. Tailwind classes are NOT
 * supported by satori — all styling must be inline. Layout uses flexbox
 * because satori's CSS subset implements flex but not grid.
 */
export function OgCard({ report, avatarUrl }: Props) {
  const accent = tierAccent(report.tier.name);
  const topBadges = report.badges.slice(0, 3);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        background: `linear-gradient(180deg, ${OG_BG_DARK_TOP} 0%, ${OG_BG_DARK} 100%)`,
        color: OG_FG,
        padding: "64px",
        fontFamily: "Inter",
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          {avatarUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={avatarUrl}
              alt=""
              width={96}
              height={96}
              style={{ borderRadius: 9999, border: `2px solid ${accent}` }}
            />
          ) : (
            <div
              style={{
                width: 96,
                height: 96,
                borderRadius: 9999,
                background: "#222",
                border: `2px solid ${accent}`,
              }}
            />
          )}
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ fontSize: 56, fontWeight: 700, lineHeight: 1.1 }}>
              {report.username}
            </div>
            <div style={{ fontSize: 22, color: OG_FG_MUTED, marginTop: 8 }}>
              github.com/{report.username}
            </div>
          </div>
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-end",
          }}
        >
          <div style={{ fontSize: 32, fontWeight: 700 }}>Skill Issue</div>
          <div style={{ fontSize: 16, color: "#666", marginTop: 4 }}>
            skill-issue-tau.vercel.app
          </div>
        </div>
      </div>

      {/* Tier + score row */}
      <div style={{ display: "flex", gap: 32, marginTop: 56, flex: 1 }}>
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: 32,
            background: `${accent}0d`,
            borderRadius: 24,
            border: `1px solid ${accent}33`,
          }}
        >
          <div style={{ fontSize: 48, fontWeight: 700, color: accent }}>
            {report.tier.name}
          </div>
          <div style={{ fontSize: 24, color: OG_FG_MUTED, marginTop: 12 }}>
            {report.tier.sub_rank}/100 within tier
          </div>
          {report.tier.next_tier && report.tier.pts_to_next != null ? (
            <div style={{ fontSize: 20, color: "#666", marginTop: 24 }}>
              next: {report.tier.next_tier} · {report.tier.pts_to_next} pts
            </div>
          ) : null}
        </div>

        <div
          style={{
            width: 280,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            background: `${accent}1a`,
            borderRadius: 24,
            border: `1px solid ${accent}55`,
          }}
        >
          <div
            style={{
              fontSize: 144,
              fontWeight: 700,
              color: accent,
              lineHeight: 1,
            }}
          >
            {report.total}
          </div>
          <div
            style={{
              fontSize: 24,
              color: accent,
              opacity: 0.7,
              marginTop: 8,
            }}
          >
            / 100
          </div>
        </div>
      </div>

      {/* Badge row */}
      <div
        style={{ display: "flex", gap: 16, marginTop: 32 }}
        data-testid="og-badge-row"
      >
        {topBadges.map((b) => (
          <div
            key={b.slug}
            style={{
              padding: "10px 20px",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 999,
              fontSize: 20,
              color: "#ddd",
            }}
          >
            {b.name}
          </div>
        ))}
      </div>
    </div>
  );
}
