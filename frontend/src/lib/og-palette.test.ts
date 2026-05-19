import { tierAccent } from "./og-palette";

describe("tierAccent", () => {
  it("maps Hobbyist to the amber accent", () => {
    expect(tierAccent("Hobbyist")).toBe("#f59e0b");
  });

  it("maps Principal Engineer to the indigo accent", () => {
    expect(tierAccent("Principal Engineer")).toBe("#818cf8");
  });

  it("maps the middle tiers to distinct hues", () => {
    const hues = new Set([
      tierAccent("Student Builder"),
      tierAccent("Entry-Level Engineer"),
      tierAccent("Professional Developer"),
      tierAccent("Senior Engineer"),
      tierAccent("Staff Engineer"),
    ]);
    expect(hues.size).toBe(5);
  });

  it("returns a deterministic fallback for unknown tier names", () => {
    expect(tierAccent("Mystery Tier" as never)).toBe("#a3a3a3");
  });
});
