"use client";

import { m } from "framer-motion";

const ITEMS = [
  {
    title: "Six deterministic signals",
    body: "Repo quality, engineering maturity, OSS & collaboration, recruiter signal, consistency, and learning trajectory.",
  },
  {
    title: "A 100-point, explainable score",
    body: "Every point traces back to evidence in your GitHub history. No black box, no vibes.",
  },
  {
    title: "AI writes the narrative, never the score",
    body: "The model only formats the story. The numbers come from pure, deterministic code.",
  },
  {
    title: "Roast or Mentor",
    body: "Pick the tone — brutally funny or genuinely constructive — over the same honest analysis.",
  },
];

export function HowItWorks() {
  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-16 sm:px-6 sm:py-24">
      <m.h2
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="text-center text-2xl font-bold tracking-tight text-foreground sm:text-3xl"
      >
        Engineering insight first. AI flavor second.
      </m.h2>
      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-6">
        {ITEMS.map((it, i) => (
          <m.div
            key={it.title}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: i * 0.06, ease: [0.16, 1, 0.3, 1] }}
            className="glass rounded-2xl p-6"
          >
            <h3 className="text-base font-semibold text-foreground">{it.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{it.body}</p>
          </m.div>
        ))}
      </div>
    </section>
  );
}
