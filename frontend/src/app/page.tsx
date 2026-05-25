"use client";

import { m } from "framer-motion";
import { SearchBar } from "@/components/search-bar";

export default function Home() {
  return (
    <div className="relative flex flex-1 flex-col items-center justify-center overflow-hidden py-12 px-4 sm:py-16 sm:px-6 md:py-20">
      {/* Ambient blobs — smaller and lighter on mobile to keep paint cheap */}
      <div className="absolute top-0 -left-4 w-48 h-48 sm:w-72 sm:h-72 bg-accent/20 rounded-full mix-blend-screen blur-[96px] sm:blur-[128px] animate-pulse" />
      <div className="absolute bottom-0 -right-4 w-48 h-48 sm:w-72 sm:h-72 bg-blue-500/10 rounded-full mix-blend-screen blur-[96px] sm:blur-[128px] animate-pulse [animation-delay:700ms]" />

      <main className="relative z-10 flex w-full max-w-4xl flex-col items-center">
        <m.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center space-y-6 text-center sm:space-y-8"
        >
          <m.span
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium uppercase tracking-wider text-muted-foreground"
          >
            Deterministic engineering reports · v0.8.6
          </m.span>

          <h1 className="text-4xl sm:text-5xl md:text-7xl font-bold tracking-tight text-gradient leading-tight">
            Skill Issue
          </h1>

          <p className="max-w-xl text-base sm:text-lg md:text-xl text-muted-foreground leading-relaxed">
            Your GitHub profile is your real resume.{" "}
            <span className="text-foreground">Skill Issue reads it honestly.</span>
          </p>

          <m.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.6 }}
            className="flex w-full justify-center pt-4 sm:pt-8"
          >
            <SearchBar />
          </m.div>

          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            transition={{ delay: 0.8, duration: 1 }}
            className="grid grid-cols-3 gap-4 pt-10 text-xs font-medium uppercase tracking-widest text-muted-foreground sm:gap-8 sm:pt-16 sm:text-sm md:gap-16"
          >
            <div className="flex flex-col gap-1">
              <span className="text-base text-foreground sm:text-lg">100</span>
              <span>Deterministic</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-base text-foreground sm:text-lg">6</span>
              <span>Analyzers</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-base text-foreground sm:text-lg">0</span>
              <span>Hallucinations</span>
            </div>
          </m.div>
        </m.div>
      </main>

      <div className="absolute inset-0 -z-10 h-full w-full bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:2rem_2rem] sm:bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
    </div>
  );
}
