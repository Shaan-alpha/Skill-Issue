import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-white/5 px-4 py-6 sm:px-6">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 text-xs text-muted-foreground sm:flex-row">
        <p>© 2026 Skill Issue</p>
        <nav className="flex items-center gap-4">
          <Link href="/privacy" className="transition-colors hover:text-foreground">
            Privacy
          </Link>
          <Link href="/terms" className="transition-colors hover:text-foreground">
            Terms
          </Link>
          <a
            href="https://github.com/Shaan-alpha/Skill-Issue"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-foreground"
          >
            GitHub
          </a>
        </nav>
      </div>
    </footer>
  );
}
