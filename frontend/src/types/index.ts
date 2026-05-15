export type DeveloperCategory =
  | "Student Builder"
  | "Entry-Level Engineer"
  | "Professional Developer"
  | "Senior Engineer"
  | "OSS Contributor"
  | "Indie Hacker";

export interface Evidence {
  signal: string;
  detail: string;
  weight: number;
}

export interface ScoreResult {
  points: number;
  max_points: number;
  evidence: Evidence[];
}

export interface ScoreBreakdown {
  repo_quality: ScoreResult;
  engineering_maturity: ScoreResult;
  oss_collab: ScoreResult;
  consistency: ScoreResult;
  recruiter_signal: ScoreResult;
  learning_trajectory: ScoreResult;
}

export interface Report {
  username: string;
  category: DeveloperCategory;
  breakdown: ScoreBreakdown;
  total: number;
  generated_at: string;
}
