"use client";

import { motion } from "framer-motion";
import { SearchBar } from "@/components/search-bar";

export default function Home() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden py-20 px-6">
      {/* Animated background blobs */}
      <div className="absolute top-0 -left-4 w-72 h-72 bg-accent/20 rounded-full mix-blend-screen filter blur-[128px] animate-pulse" />
      <div className="absolute bottom-0 -right-4 w-72 h-72 bg-blue-500/10 rounded-full mix-blend-screen filter blur-[128px] animate-pulse delay-700" />
      
      <main className="relative z-10 flex flex-col items-center max-w-4xl w-full">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col items-center text-center space-y-8"
        >
          {/* Badge */}
          <motion.span 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="px-3 py-1 rounded-full border border-white/10 bg-white/5 text-xs font-medium tracking-wider text-muted-foreground uppercase"
          >
            v0.1.0 Backend MVP Shipped
          </motion.span>

          {/* Title */}
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-gradient sm:leading-tight">
            Skill Issue
          </h1>
          
          {/* Subtitle */}
          <p className="max-w-xl text-lg md:text-xl text-muted-foreground leading-relaxed">
            Your GitHub profile is your real resume. <br />
            <span className="text-foreground">Skill Issue reads it honestly.</span>
          </p>

          {/* Action Area */}
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4, duration: 0.6 }}
            className="w-full flex justify-center pt-8"
          >
            <SearchBar />
          </motion.div>

          {/* Footer stats or social proof */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.5 }}
            transition={{ delay: 0.8, duration: 1 }}
            className="pt-16 grid grid-cols-3 gap-8 md:gap-16 text-sm font-medium uppercase tracking-widest text-muted-foreground"
          >
            <div className="flex flex-col gap-1">
              <span className="text-foreground text-lg">100</span>
              <span>Deterministic</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-foreground text-lg">6</span>
              <span>Analyzers</span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-foreground text-lg">0</span>
              <span>Hallucinations</span>
            </div>
          </motion.div>
        </motion.div>
      </main>

      {/* Hero background grid effect */}
      <div className="absolute inset-0 -z-10 h-full w-full bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
    </div>
  );
}
