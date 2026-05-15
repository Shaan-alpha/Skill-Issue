"use client";

import { motion } from "framer-motion";
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
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Report, ScoreResult } from "@/types";

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
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <Card className="glass glass-hover h-full border-none shadow-none">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
            {title}
          </CardTitle>
          <div className="h-4 w-4 text-accent">{icon}</div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold">{points}</span>
            <span className="text-sm text-muted-foreground">/ {max_points}</span>
          </div>
          <Progress value={(points / max_points) * 100} className="h-1.5 bg-white/5" />
          <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
        </CardContent>
      </Card>
    </motion.div>
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
    <div className="min-h-screen bg-background py-12 px-6">
      <div className="max-w-6xl mx-auto space-y-12">
        <header className="flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors group"
          >
            <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
            Back to search
          </Link>
          <div className="flex items-center gap-4">
            <Badge variant="outline" className="border-white/10 bg-white/5 font-mono text-xs">
              ANALYSIS: {report.username.toUpperCase()}
            </Badge>
            <Link
              href={`https://github.com/${report.username}`}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open ${report.username}'s GitHub profile`}
              className="p-2 rounded-full glass glass-hover"
            >
              <ExternalLink className="h-4 w-4" />
            </Link>
          </div>
        </header>

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6 }}
            className="lg:col-span-1 glass p-8 rounded-3xl flex flex-col items-center justify-center text-center space-y-4"
          >
            <span className="text-sm font-medium text-muted-foreground uppercase tracking-widest">
              Aggregate Score
            </span>
            <div className="relative flex items-center justify-center">
              <svg className="w-48 h-48 transform -rotate-90">
                <circle
                  cx="96"
                  cy="96"
                  r="88"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="4"
                  className="text-white/5"
                />
                <motion.circle
                  cx="96"
                  cy="96"
                  r="88"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="4"
                  strokeDasharray={552.92}
                  initial={{ strokeDashoffset: 552.92 }}
                  animate={{ strokeDashoffset: 552.92 * (1 - report.total / 100) }}
                  transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
                  className="text-accent"
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute text-6xl font-bold">{report.total}</span>
            </div>
            <div className="space-y-1">
              <h2 className="text-xl font-semibold">{report.category}</h2>
              <p className="text-xs text-muted-foreground">
                ID: SKILL-ISSUE-{report.username.toUpperCase()}-01
              </p>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="lg:col-span-2 glass p-8 rounded-3xl flex flex-col justify-center space-y-6"
          >
            <div className="space-y-2">
              <Badge className="bg-accent/10 text-accent border-accent/20">Deterministic</Badge>
              <h3 className="text-2xl md:text-3xl font-semibold text-gradient">
                Engineering Report
              </h3>
            </div>
            <p className="text-lg text-muted-foreground leading-relaxed">
              {report.total} / 100 across six signals. Every point is backed by evidence — no
              hallucinations, no vibes. AI narrative arrives in v0.3.0.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4">
              <div className="space-y-1">
                <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-tighter">
                  Reliability
                </p>
                <p className="text-sm font-medium">Deterministic</p>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-tighter">
                  Insights
                </p>
                <p className="text-sm font-medium">Evidence-based</p>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-tighter">
                  Mode
                </p>
                <p className="text-sm font-medium">Standard</p>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-tighter">
                  Verified
                </p>
                <p className="text-sm font-medium text-accent">GitHub API</p>
              </div>
            </div>
          </motion.div>
        </section>

        <section className="space-y-6">
          <div className="flex items-center gap-4">
            <h4 className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground">
              Scoring Matrix
            </h4>
            <div className="h-px flex-1 bg-white/5" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((item, i) => (
              <ScoreItem
                key={item.name}
                title={item.name}
                result={item.result}
                icon={item.icon}
                description={item.desc}
                delay={0.1 * i + 0.5}
              />
            ))}
          </div>
        </section>

        <footer className="pt-12 text-center text-[10px] text-muted-foreground uppercase tracking-widest space-y-2">
          <p>Skill Issue — GitHub Reputation Protocol v0.1.0</p>
        </footer>
      </div>

      <div className="fixed inset-0 -z-10 bg-[linear-gradient(to_right,#80808005_1px,transparent_1px),linear-gradient(to_bottom,#80808005_1px,transparent_1px)] bg-[size:2rem_2rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
    </div>
  );
}
