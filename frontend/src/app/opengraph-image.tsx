import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

export const alt = "Skill Issue — your GitHub, read honestly";
export const size = { width: 1200, height: 630 } as const;
export const contentType = "image/png";

export default async function Image() {
  const [interMedium, interBold] = await Promise.all([
    readFile(join(process.cwd(), "public/fonts/Inter-Medium.ttf")),
    readFile(join(process.cwd(), "public/fonts/Inter-Bold.ttf")),
  ]);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#0a0a0a",
          color: "#fafafa",
          fontFamily: "Inter",
          padding: 80,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 30,
            fontWeight: 500,
            color: "#a1a1aa",
            textTransform: "uppercase",
            letterSpacing: 6,
          }}
        >
          Deterministic engineering reports
        </div>
        <div style={{ fontSize: 132, fontWeight: 700, marginTop: 12 }}>Skill Issue</div>
        <div style={{ fontSize: 40, fontWeight: 500, color: "#d4d4d8", marginTop: 20 }}>
          Your GitHub profile is your real resume. We read it honestly.
        </div>
        <div style={{ display: "flex", gap: 72, marginTop: 56, fontSize: 28, color: "#a1a1aa" }}>
          <div style={{ display: "flex" }}>100 · deterministic</div>
          <div style={{ display: "flex" }}>6 · analyzers</div>
          <div style={{ display: "flex" }}>0 · hallucinations</div>
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [
        { name: "Inter", data: interMedium, weight: 500, style: "normal" },
        { name: "Inter", data: interBold, weight: 700, style: "normal" },
      ],
    },
  );
}
