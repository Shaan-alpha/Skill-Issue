import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const replace = vi.fn();
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(search),
}));

import { AuthNotice } from "../auth-notice";

describe("AuthNotice", () => {
  beforeEach(() => {
    replace.mockReset();
    search = "";
  });

  it("says sign-in didn't complete when the callback failed", () => {
    search = "auth=failed";
    render(<AuthNotice />);
    expect(screen.getByRole("status")).toHaveTextContent(/sign-in didn.t complete/i);
  });

  it("says sign-in was cancelled when the user backed out on GitHub", () => {
    search = "auth=cancelled";
    render(<AuthNotice />);
    expect(screen.getByRole("status")).toHaveTextContent(/cancelled/i);
  });

  it("renders nothing for an ordinary visit or an unknown value", () => {
    search = "auth=<script>";
    const { container } = render(<AuthNotice />);
    expect(container).toBeEmptyDOMElement();
  });

  it("dismisses and drops the parameter from the address bar", () => {
    search = "auth=failed";
    render(<AuthNotice />);
    fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(replace).toHaveBeenCalledWith("/", { scroll: false });
  });
});
