import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import PrivacyPage from "@/app/privacy/page";
import TermsPage from "@/app/terms/page";
import { SiteFooter } from "@/components/site-footer";

describe("legal pages", () => {
  it("privacy page shows its heading and the contact email", () => {
    render(<PrivacyPage />);
    expect(
      screen.getByRole("heading", { name: /privacy policy/i, level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByText("shaansatsangi.cse@gmail.com")).toBeInTheDocument();
  });

  it("terms page shows its heading and the governing law", () => {
    render(<TermsPage />);
    expect(
      screen.getByRole("heading", { name: /terms of service/i, level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByText(/laws of India/i)).toBeInTheDocument();
  });

  it("footer links to privacy and terms", () => {
    render(<SiteFooter />);
    expect(screen.getByRole("link", { name: /privacy/i })).toHaveAttribute("href", "/privacy");
    expect(screen.getByRole("link", { name: /terms/i })).toHaveAttribute("href", "/terms");
  });
});
