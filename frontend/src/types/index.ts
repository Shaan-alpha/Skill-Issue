export type TierName =
  | "Hobbyist"
  | "Student Builder"
  | "Entry-Level Engineer"
  | "Professional Developer"
  | "Senior Engineer"
  | "Staff Engineer"
  | "Principal Engineer";

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

export interface Badge {
  slug: string;
  name: string;
  evidence: string;
}

export interface TierInfo {
  name: TierName;
  sub_rank: number;
  band: [number, number];
  next_tier: TierName | null;
  pts_to_next: number | null;
  prev_tier: TierName | null;
  pts_above_prev: number;
}

export interface Report {
  username: string;
  tier: TierInfo;
  badges: Badge[];
  breakdown: ScoreBreakdown;
  total: number;
  generated_at: string;
}

export type NarrativeMode = "roast" | "mentor";

export type Session =
  | { user: { id: number; login: string; name: string | null; avatar_url: string | null } }
  | null;

export interface SavedAnalysis {
  id: number;
  target_login: string;
  is_public: boolean;
  share_slug: string | null;
  latest_run: {
    total_score: number;
    tier_name: string;
    completed_at: string;
  } | null;
}

export interface MeAnalysesResponse {
  analyses: SavedAnalysis[];
  page: number;
  total: number;
}

export interface ShareResponse {
  share_slug: string;
  share_url: string;
}

export interface SharedAnalysisPayload {
  report: Report;
  owner: { login: string; avatar_url: string | null };
  shared_at: string;
}
