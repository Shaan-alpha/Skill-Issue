from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

TierName = Literal[
    "Hobbyist",
    "Student Builder",
    "Entry-Level Engineer",
    "Professional Developer",
    "Senior Engineer",
    "Staff Engineer",
    "Principal Engineer",
]


class TierInfo(BaseModel):
    name: TierName
    sub_rank: int = Field(ge=0, le=100)
    band: tuple[int, int]
    next_tier: TierName | None = None
    pts_to_next: int | None = None
    prev_tier: TierName | None = None
    pts_above_prev: int = 0


class Badge(BaseModel):
    slug: str  # kebab-case stable identifier
    name: str  # display name
    evidence: str  # one-line trigger explanation


class Evidence(BaseModel):
    signal: str
    detail: str
    weight: int


class ScoreResult(BaseModel):
    points: int = Field(ge=0)
    max_points: int = Field(gt=0)
    evidence: list[Evidence] = Field(default_factory=list)

    @field_validator("points")
    @classmethod
    def _points_le_max(cls, v: int, info: ValidationInfo) -> int:
        max_points = info.data.get("max_points")
        if max_points is not None and v > max_points:
            raise ValueError(f"points {v} > max_points {max_points}")
        return v


class Repo(BaseModel):
    name: str
    full_name: str
    primary_language: str | None
    stars: int
    forks: int
    is_fork: bool
    has_readme: bool
    has_tests: bool
    has_ci: bool
    deployment_hints: list[str]  # e.g. ["dockerfile", "vercel.json"]
    size_kb: int = 0
    last_commit_at: datetime | None
    created_at: datetime


class Profile(BaseModel):
    username: str
    bio: str | None
    profile_readme_chars: int
    followers: int
    public_repos: int
    languages: dict[str, int]  # language -> bytes
    repos: list[Repo]
    external_prs_merged: int
    external_reviews: int
    external_orgs: set[str] = Field(default_factory=set)
    commit_dates: list[datetime]
    account_created_at: datetime
    # Recruiter Signal fields
    company: str | None = None
    blog: str | None = None
    hireable: bool = False
    has_sponsors_listing: bool = False
    is_github_star: bool = False
    is_developer_program_member: bool = False
    # --- v0.3.0 depth signals (populated only when base tier unlocks them) ---
    licensed_repos: list[str] = Field(default_factory=list)
    workflow_counts: dict[str, int] = Field(default_factory=dict)
    readme_lengths: dict[str, int] = Field(default_factory=dict)
    review_avg_comments: int | None = None
    dep_files: dict[str, list[str]] = Field(default_factory=dict)
    commit_message_quality: int | None = None
    cross_repo_contribution_count: int | None = None


class ScoreBreakdown(BaseModel):
    repo_quality: ScoreResult
    engineering_maturity: ScoreResult
    oss_collab: ScoreResult
    consistency: ScoreResult
    recruiter_signal: ScoreResult
    learning_trajectory: ScoreResult

    def total(self) -> int:
        return (
            self.repo_quality.points
            + self.engineering_maturity.points
            + self.oss_collab.points
            + self.consistency.points
            + self.recruiter_signal.points
            + self.learning_trajectory.points
        )


class Report(BaseModel):
    username: str
    tier: TierInfo
    badges: list[Badge] = Field(default_factory=list)
    breakdown: ScoreBreakdown
    total: int = Field(ge=0, le=100)
    generated_at: datetime
