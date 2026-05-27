import { fireEvent, render, screen, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import { SearchBar } from "../search-bar";

describe("SearchBar", () => {
  beforeEach(() => push.mockReset());

  it("re-enables the button on pageshow after a navigation (bfcache restore)", async () => {
    render(<SearchBar />);
    const input = screen.getByLabelText("GitHub username");
    fireEvent.change(input, { target: { value: "shaan-alpha" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze profile" }));

    // After submit the button is in the loading state (disabled).
    expect(screen.getByRole("button", { name: "Analyze profile" })).toBeDisabled();
    expect(push).toHaveBeenCalledWith("/u/shaan-alpha");

    // Browser back restores the page from bfcache -> pageshow fires.
    act(() => {
      window.dispatchEvent(new Event("pageshow"));
    });

    expect(screen.getByRole("button", { name: "Analyze profile" })).not.toBeDisabled();
  });
});
