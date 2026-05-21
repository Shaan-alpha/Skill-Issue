import fs from "node:fs";
import path from "node:path";

const stats = JSON.parse(
  fs.readFileSync(".next/diagnostics/route-bundle-stats.json", "utf8"),
);
const routes = ["/u/[username]", "/share/[slug]", "/"];

for (const r of stats.filter((s) => routes.includes(s.route))) {
  console.log(`\n=== ${r.route} ===`);
  console.log(
    `  total uncompressed: ${Math.round(r.firstLoadUncompressedJsBytes / 1024)} KB`,
  );
  const sized = r.firstLoadChunkPaths
    .map((p) => {
      const abs = p.split("\\").join(path.sep);
      try {
        return { p: abs, sz: fs.statSync(abs).size };
      } catch {
        return { p: abs, sz: 0 };
      }
    })
    .sort((a, b) => b.sz - a.sz);
  for (const c of sized.slice(0, 6)) {
    console.log(
      `  ${c.p.split(path.sep).pop().padEnd(34)} ${(c.sz / 1024).toFixed(1)} KB`,
    );
  }
}
