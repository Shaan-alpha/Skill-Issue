import { fireEvent, render, screen } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

import { SearchBar } from "../search-bar";

describe("SearchBar", () => {
  beforeEach(() => push.mockReset());

  function submit(value: string) {
    render(<SearchBar />);
    fireEvent.change(screen.getByLabelText("GitHub username"), { target: { value } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze profile" }));
  }

  it("navigates to the normalized username on submit", () => {
    submit("shaan-alpha");
    expect(push).toHaveBeenCalledWith("/u/shaan-alpha");
  });

  it("extracts the username from a pasted github.com URL", () => {
    submit("https://github.com/shaan-alpha/some-repo");
    expect(push).toHaveBeenCalledWith("/u/shaan-alpha");
  });

  it("strips a leading @ handle", () => {
    submit("@shaan-alpha");
    expect(push).toHaveBeenCalledWith("/u/shaan-alpha");
  });

  it("shows an error and does not navigate on an invalid username", () => {
    submit("-bad-");
    expect(push).not.toHaveBeenCalled();
    expect(screen.getByText(/valid GitHub username/i)).toBeInTheDocument();
  });
});
