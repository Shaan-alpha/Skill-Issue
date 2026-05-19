import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import { CardActions } from "./card-actions";

const writeText = vi.fn(async () => undefined);

afterEach(() => {
  vi.restoreAllMocks();
  writeText.mockReset();
});

function withClipboard() {
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText, write: vi.fn(async () => undefined) },
  });
}

describe("CardActions", () => {
  it("renders three actions", () => {
    withClipboard();
    render(
      <CardActions
        imageUrl="/u/octocat/opengraph-image"
        pageUrl="https://x.test/u/octocat"
      />,
    );
    expect(screen.getByRole("button", { name: /copy png/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /download png/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /copy url/i })).toBeInTheDocument();
  });

  it("copies the page URL on Copy URL click", async () => {
    withClipboard();
    render(
      <CardActions imageUrl="/x.png" pageUrl="https://x.test/u/octocat" />,
    );
    fireEvent.click(screen.getByRole("button", { name: /copy url/i }));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith("https://x.test/u/octocat");
    });
  });

  it("renders Download PNG as a real <a download> with the correct href", () => {
    withClipboard();
    render(
      <CardActions imageUrl="/u/octocat/opengraph-image" pageUrl="https://x.test" />,
    );
    const a = screen.getByRole("link", { name: /download png/i });
    expect(a).toHaveAttribute("href", "/u/octocat/opengraph-image");
    expect(a).toHaveAttribute("download");
  });
});
