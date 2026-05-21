import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { ShareAttribution } from "./share-attribution";

describe("ShareAttribution", () => {
  it("renders a sized image with the GitHub avatar URL", () => {
    const { container } = render(
      <ShareAttribution
        login="octocat"
        avatarUrl="https://avatars.githubusercontent.com/u/583231?v=4"
        cardHref="/u/octocat/card"
      />,
    );
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    expect(img!.getAttribute("width")).toBe("20");
    expect(img!.getAttribute("height")).toBe("20");
    expect(img!.getAttribute("alt")).toBe("");
  });

  it("omits the image when no avatarUrl is provided", () => {
    const { container } = render(
      <ShareAttribution login="octocat" avatarUrl={null} cardHref="/u/octocat/card" />,
    );
    expect(container.querySelector("img")).toBeNull();
  });
});
