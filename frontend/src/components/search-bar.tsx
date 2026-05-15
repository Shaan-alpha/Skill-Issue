"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function SearchBar() {
  const [username, setUsername] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) return;

    setIsLoading(true);
    // Navigate to the analysis page
    router.push(`/u/${username.trim()}`);
  };

  return (
    <form 
      onSubmit={handleSearch}
      className="relative flex w-full max-w-md items-center gap-2"
    >
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="GitHub username..."
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={isLoading}
          className="h-12 w-full border-white/10 bg-white/5 pl-10 pr-4 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-0"
        />
      </div>
      <Button 
        type="submit" 
        size="icon"
        disabled={isLoading || !username.trim()}
        className="h-12 w-12 rounded-lg bg-white text-black transition-all hover:bg-white/90 hover:scale-105 active:scale-95 disabled:opacity-50"
      >
        {isLoading ? (
          <Loader2 className="h-5 w-5 animate-spin" />
        ) : (
          <ArrowRight className="h-5 w-5" />
        )}
      </Button>
    </form>
  );
}
