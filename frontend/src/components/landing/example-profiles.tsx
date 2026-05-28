"use client";

import { m } from "framer-motion";
import Link from "next/link";
import { ArrowRight } from "lucide-react";

const PROFILES = [
  { username: "torvalds", name: "Linus Torvalds" },
  { username: "gaearon", name: "Dan Abramov" },
  { username: "sindresorhus", name: "Sindre Sorhus" },
  { username: "antfu", name: "Anthony Fu" },
  { username: "yyx990803", name: "Evan You" },
  { username: "tj", name: "TJ Holowaychuk" },
];

export function ExampleProfiles() {
  return (
    <section className="mx-auto w-full max-w-5xl px-4 py-16 sm:px-6 sm:py-24">
      <div className="text-center">
        <h2 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          See it in action
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">Real reports — click any profile.</p>
      </div>
      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3">
        {PROFILES.map((p, i) => (
          <m.div
            key={p.username}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.5, delay: i * 0.05, ease: [0.16, 1, 0.3, 1] }}
          >
            <Link
              href={`/u/${p.username}`}
              className="glass group flex items-center gap-4 rounded-2xl p-4 transition-colors hover:bg-white/10"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`https://github.com/${p.username}.png?size=80`}
                alt=""
                width={48}
                height={48}
                loading="lazy"
                className="size-12 rounded-full border border-white/10"
              />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-foreground">{p.name}</p>
                <p className="truncate text-xs text-muted-foreground">@{p.username}</p>
              </div>
              <span className="flex items-center gap-1 text-xs text-muted-foreground transition-colors group-hover:text-foreground">
                View
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
            </Link>
          </m.div>
        ))}
      </div>
    </section>
  );
}
