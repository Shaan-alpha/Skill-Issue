import { describe, expect, it } from "vitest";
import { closeOffTruncated, stripMarkdownEmphasis } from "./narrative-text";

describe("stripMarkdownEmphasis", () => {
  it("unwraps bold without eating the words", () => {
    expect(stripMarkdownEmphasis("You shipped **four** repos")).toBe(
      "You shipped four repos"
    );
  });

  it("unwraps several bold runs in one paragraph", () => {
    expect(
      stripMarkdownEmphasis("**92% README coverage** and **zero tests**.")
    ).toBe("92% README coverage and zero tests.");
  });

  it("unwraps single-asterisk italics", () => {
    expect(stripMarkdownEmphasis("that is *technically* a commit")).toBe(
      "that is technically a commit"
    );
  });

  it("unwraps inline code spans", () => {
    expect(stripMarkdownEmphasis("add `test.yml` to the repo")).toBe(
      "add test.yml to the repo"
    );
  });

  it("strips markdown headings at line start", () => {
    expect(stripMarkdownEmphasis("## The Verdict\nYou lost.")).toBe(
      "The Verdict\nYou lost."
    );
  });

  it("hides a half-streamed marker instead of flashing raw asterisks", () => {
    // Mid-stream the closing ** has not arrived yet.
    expect(stripMarkdownEmphasis("You shipped **")).toBe("You shipped ");
  });

  it("leaves snake_case identifiers alone", () => {
    // Underscores are load-bearing in identifiers, so they are never stripped.
    expect(stripMarkdownEmphasis("the engineering_maturity bucket")).toBe(
      "the engineering_maturity bucket"
    );
  });

  it("leaves ordinary prose untouched", () => {
    const prose = "Your commit history says a lot. None of it is good.";
    expect(stripMarkdownEmphasis(prose)).toBe(prose);
  });

  it("handles an empty string", () => {
    expect(stripMarkdownEmphasis("")).toBe("");
  });
});

describe("closeOffTruncated", () => {
  it("drops a sentence the model stopped in the middle of", () => {
    expect(
      closeOffTruncated("You shipped four repos. Your README is a haiku and")
    ).toBe("You shipped four repos.");
  });

  it("leaves an already-complete ending alone", () => {
    const complete = "You shipped four repos. That is the whole story.";
    expect(closeOffTruncated(complete)).toBe(complete);
  });

  it("keeps text that has no sentence boundary at all", () => {
    // Better a ragged line than an empty card.
    expect(closeOffTruncated("You shipped four repos and")).toBe(
      "You shipped four repos and"
    );
  });

  it("respects a closing quote after the full stop", () => {
    const quoted = 'Your bio reads "move fast."';
    expect(closeOffTruncated(quoted)).toBe(quoted);
  });

  it("handles an empty string", () => {
    expect(closeOffTruncated("")).toBe("");
  });
});
