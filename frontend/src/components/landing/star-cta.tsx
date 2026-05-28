"use client";

import { m } from "framer-motion";
import { Star } from "lucide-react";

export function StarCta() {
  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-16 text-center sm:px-6 sm:py-20">
      <m.div
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="flex flex-col items-center gap-4"
      >
        <h2 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Like it? Star it on GitHub.
        </h2>
        <p className="max-w-md text-sm text-muted-foreground">
          Skill Issue is built in the open. A star helps more developers find it.
        </p>
        <a
          href="https://github.com/Shaan-alpha/Skill-Issue"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-medium text-black transition-all hover:scale-105 hover:bg-white/90 active:scale-95"
        >
          <Star className="h-4 w-4" aria-hidden="true" />
          Star on GitHub
        </a>
      </m.div>
    </section>
  );
}
