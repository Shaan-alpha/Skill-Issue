"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// GitHub usernames: 1-39 chars, alphanumeric or single hyphens, no leading
// or trailing hyphen. Mirrors the backend validator in app/main.py.
const USERNAME_RE = /^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$/;

function normalize(raw: string): string {
  let v = raw.trim();
  // Accept https://github.com/<user>, github.com/<user>, or @user.
  v = v.replace(/^https?:\/\/(www\.)?github\.com\//i, "");
  v = v.replace(/^github\.com\//i, "");
  v = v.replace(/^@/, "");
  // Drop a trailing slash or path segment.
  v = v.split(/[/?#]/)[0] ?? "";
  return v;
}

export function SearchBar() {
  const [raw, setRaw] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  // After navigating to /u/<user> the browser may restore THIS page from the
  // bfcache on back-navigation, with isLoading still true (stuck spinner +
  // disabled input). Reset it whenever the page is shown again.
  useEffect(() => {
    const reset = () => setIsLoading(false);
    window.addEventListener("pageshow", reset);
    return () => window.removeEventListener("pageshow", reset);
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const username = normalize(raw);
    if (!username) {
      setError("Enter a GitHub username.");
      return;
    }
    if (!USERNAME_RE.test(username)) {
      setError("That doesn't look like a valid GitHub username.");
      return;
    }
    setError(null);
    setIsLoading(true);
    router.push(`/u/${username}`);
  };

  return (
    <div className="w-full max-w-md space-y-2">
      <form onSubmit={handleSearch} className="relative flex w-full items-center gap-2">
        <div className="relative flex-1">
          <Search
            className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            placeholder="GitHub username"
            value={raw}
            onChange={(e) => {
              setRaw(e.target.value);
              if (error) setError(null);
            }}
            disabled={isLoading}
            aria-label="GitHub username"
            aria-invalid={error ? true : undefined}
            autoCapitalize="off"
            autoCorrect="off"
            spellCheck={false}
            className="h-12 w-full border-white/10 bg-white/5 pl-10 pr-4 text-base placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-0"
          />
        </div>
        <Button
          type="submit"
          size="icon"
          disabled={isLoading || !raw.trim()}
          aria-label="Analyze profile"
          className="h-12 w-12 rounded-lg bg-white text-black transition-all hover:bg-white/90 hover:scale-105 active:scale-95 disabled:opacity-50"
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
          ) : (
            <ArrowRight className="h-5 w-5" aria-hidden="true" />
          )}
        </Button>
      </form>
      <p
        className={`min-h-[1.25rem] text-xs ${
          error ? "text-destructive-foreground/80" : "text-muted-foreground/50"
        }`}
        aria-live="polite"
      >
        {error ?? "Tip: paste a github.com URL and we'll pull the username out."}
      </p>
    </div>
  );
}
