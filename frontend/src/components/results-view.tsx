"use client";

import { m } from "framer-motion";
import {
  ArrowLeft,
  ExternalLink,
  Award,
  Terminal,
  Zap,
  Layers,
  GitPullRequest,
  Target,
} from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress, ProgressLabel } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Report, ScoreResult } from "@/types";
import { PositionBar } from "@/components/position-bar";
import { BadgeRow } from "@/components/badge-row";

interface ScoreCardProps {
  title: string;
  result: ScoreResult;
  icon: React.ReactNode;
  description: string;
  delay: number;
}

function ScoreItem({ title, result, icon, description, delay }: ScoreCardProps) {
  const { points, max_points } = result;
  return (
    <m.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card className="glass glass-hover h-full border-none shadow-none">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
            {title}
          </CardTitle>
          <div className="h-4 w-4 text-accent" aria-hidden="true">{icon}</div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold">{points}</span>
            <span className="text-sm text-muted-foreground">/ {max_points}</span>
          </div>
          <Progress value={(points / max_points) * 100} className="h-1.5 bg-white/5">
            <ProgressLabel className="sr-only">
              {title}: {points} of {max_points} points
            </ProgressLabel>
          </Progress>
          <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
        </CardContent>
      </Card>
    </m.div>
  );
}

export function ResultsView({ report }: { report: Report }) {
  const { breakdown } = report;
  const items = [
    {
      name: "Repo Quality",
      result: breakdown.repo_quality,
      icon: <Terminal />,
      desc: "README quality, folder structure, and license hygiene.",
    },
    {
      name: "Engineering Maturity",
      result: breakdown.engineering_maturity,
      icon: <Layers />,
      desc: "Testing culture, CI/CD usage, and modular design.",
    },
    {
      name: "OSS & Collaboration",
      result: breakdown.oss_collab,
      icon: <GitPullRequest />,
      desc: "External PRs, issue discussions, and community engagement.",
    },
    {
      name: "Consistency",
      result: breakdown.consistency,
      icon: <Zap />,
      desc: "Commit cadence and long-term project maintenance.",
    },
    {
      name: "Recruiter Signal",
      result: breakdown.recruiter_signal,
      icon: <Target />,
      desc: "Profile README, portfolio presence, and stack relevance.",
    },
    {
      name: "Learning Trajectory",
      result: breakdown.learning_trajectory,
      icon: <Award />,
      desc: "Skill evolution and project complexity growth.",
    },
  ];

  return (
    <div className="min-h-screen bg-background px-4 py-6 sm:px-6 sm:py-12">
      <main className="mx-auto max-w-6xl space-y-8 sm:space-y-12">
        <h1 className="sr-only">Engineering report for {report.username}</h1>
        <header className="flex flex-wrap items-center justify-between gap-3">
          <Link
            href="/"
            className="group flex items-center gap-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" aria-hidden="true" />
            Back to search
          </Link>
          <div className="flex items-center gap-3">
            <Badge
              variant="outline"
              className="max-w-[60vw] truncate border-white/10 bg-white/5 font-mono text-xs"
            >
              ANALYSIS: {report.username.toUpperCase()}
            </Badge>
            <Link
              href={`https://github.com/${report.username}`}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open ${report.username}'s GitHub profile`}
              className="glass glass-hover rounded-full p-2"
            >
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </header>

        <PositionBar tier={report.tier} total={report.total} />
        <BadgeRow badges={report.badges} />

        <section className="grid grid-cols-1 gap-6 lg:grid-cols-3 lg:gap-8">
          <m.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
            className="glass flex flex-col items-center justify-center space-y-4 rounded-3xl p-6 text-center sm:p-8 lg:col-span-1"
          >
            <span className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
              Aggregate Score
            </span>
            <div className="relative flex items-center justify-center">
              <svg
                viewBox="0 0 192 192"
                className="h-36 w-36 -rotate-90 sm:h-48 sm:w-48"
                aria-hidden="true"
              >
                <circle
                  cx="96"
                  cy="96"
                  r="88"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="4"
                  className="text-white/5"
                />
                <m.circle
                  cx="96"
                  cy="96"
                  r="88"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="4"
                  strokeDasharray={552.92}
                  initial={{ strokeDashoffset: 552.92 }}
                  animate={{ strokeDashoffset: 552.92 * (1 - report.total / 100) }}
                  transition={{ duration: 1.2, ease: "easeOut", delay: 0.1 }}
                  className="text-accent"
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute text-5xl font-bold sm:text-6xl">{report.total}</span>
            </div>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold sm:text-xl">
                {report.tier.name}
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  · {report.tier.sub_rank}/100
                </span>
              </h2>
              <p className="break-all text-xs text-muted-foreground">
                ID: SKILL-ISSUE-{report.username.toUpperCase()}-01
              </p>
            </div>
          </m.div>

          <m.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="glass flex flex-col justify-center space-y-5 rounded-3xl p-6 sm:space-y-6 sm:p-8 lg:col-span-2"
          >
            <div className="space-y-2">
              <Badge className="border-accent/20 bg-accent/10 text-accent">Deterministic</Badge>
              <h2 className="text-xl font-semibold text-gradient sm:text-2xl md:text-3xl">
                Engineering Report
              </h2>
            </div>
            <p className="text-base leading-relaxed text-muted-foreground sm:text-lg">
              {report.total} / 100 across six signals. Every point is backed by evidence — no
              hallucinations, no vibes. AI narrative arrives in v0.3.0.
            </p>
            <div className="grid grid-cols-2 gap-4 pt-2 sm:grid-cols-4 sm:pt-4">
              <div className="space-y-1">
                <p className="text-xs font-bold uppercase tracking-tighter text-muted-foreground">
                  Reliability
                </p>
                <p className="text-sm font-medium">Deterministic</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold uppercase tracking-tighter text-muted-foreground">
                  Insights
                </p>
                <p className="text-sm font-medium">Evidence-based</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold uppercase tracking-tighter text-muted-foreground">
                  Mode
                </p>
                <p className="text-sm font-medium">Standard</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold uppercase tracking-tighter text-muted-foreground">
                  Verified
                </p>
                <p className="text-sm font-medium text-accent">GitHub API</p>
              </div>
            </div>
          </m.div>
        </section>

        <section className="space-y-6">
          <div className="flex items-center gap-4">
            <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground sm:text-sm">
              Scoring Matrix
            </h2>
            <div className="h-px flex-1 bg-white/5" />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:gap-6 md:grid-cols-2 lg:grid-cols-3">
            {items.map((item, i) => (
              <ScoreItem
                key={item.name}
                title={item.name}
                result={item.result}
                icon={item.icon}
                description={item.desc}
                delay={0.05 * i + 0.3}
              />
            ))}
          </div>
        </section>

        <footer className="space-y-2 pt-8 text-center text-xs uppercase tracking-widest text-muted-foreground sm:pt-12">
          <p>Skill Issue — GitHub Reputation Protocol v0.1.0</p>
        </footer>
      </main>

      <div className="fixed inset-0 -z-10 bg-[linear-gradient(to_right,#80808005_1px,transparent_1px),linear-gradient(to_bottom,#80808005_1px,transparent_1px)] bg-[size:2rem_2rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
    </div>
  );
}
