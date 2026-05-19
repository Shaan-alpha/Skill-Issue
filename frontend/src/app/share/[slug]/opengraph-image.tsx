import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { OgCard } from "@/components/og-card";
import { fetchReportForSlug } from "@/lib/og-card-data";

export const alt = "Skill Issue shared engineering scorecard";
export const size = { width: 1200, height: 630 } as const;
export const contentType = "image/png";

export default async function Image({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const report = await fetchReportForSlug(slug);

  const [interMedium, interBold] = await Promise.all([
    readFile(join(process.cwd(), "public/fonts/Inter-Medium.ttf")),
    readFile(join(process.cwd(), "public/fonts/Inter-Bold.ttf")),
  ]);

  return new ImageResponse(
    report ? (
      <OgCard
        report={report}
        avatarUrl={`https://github.com/${report.username}.png?size=96`}
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
        Shared analysis unavailable
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
