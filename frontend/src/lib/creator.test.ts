import { describe, it, expect } from "vitest";
import { CREATOR_LOGIN, isCreator } from "./creator";

describe("isCreator", () => {
  it("matches the creator login case-insensitively", () => {
    expect(isCreator("shaan-alpha")).toBe(true);
    expect(isCreator("Shaan-Alpha")).toBe(true);
    expect(isCreator(CREATOR_LOGIN)).toBe(true);
  });
  it("is false for anyone else", () => {
    expect(isCreator("octocat")).toBe(false);
    expect(isCreator("")).toBe(false);
  });
});
