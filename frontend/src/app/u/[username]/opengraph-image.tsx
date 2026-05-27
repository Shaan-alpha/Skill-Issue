import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { OgCard } from "@/components/og-card";
import { isCreator } from "@/lib/creator";
import { fetchReportForUser } from "@/lib/og-card-data";

export const alt = "Skill Issue engineering scorecard";
export const size = { width: 1200, height: 630 } as const;
export const contentType = "image/png";

export default async function Image({
  params,
}: {
  params: Promise<{ username: string }>;
}) {
  const { username } = await params;
  const report = await fetchReportForUser(username);

  const [interMedium, interBold] = await Promise.all([
    readFile(join(process.cwd(), "public/fonts/Inter-Medium.ttf")),
    readFile(join(process.cwd(), "public/fonts/Inter-Bold.ttf")),
  ]);

  return new ImageResponse(
    report ? (
      <OgCard
        report={report}
        avatarUrl={`https://github.com/${report.username}.png?size=96`}
        creator={isCreator(report.username)}
      />
    ) : (
      <div
        style={{
          width: "100%",
          height: "100%",
          background: "#0a0a0a",
          color: "#fafafa",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "Inter",
          fontSize: 48,
        }}
      >
        @{username} — analysis unavailable
      </div>
    ),
    {
      ...size,
      fonts: [
        { name: "Inter", data: interMedium, weight: 500, style: "normal" },
        { name: "Inter", data: interBold, weight: 700, style: "normal" },
      ],
      headers: {
        "cache-control":
          "public, s-maxage=300, stale-while-revalidate=86400, max-age=0",
      },
    },
  );
}
