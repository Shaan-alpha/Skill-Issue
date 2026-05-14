from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator

DeveloperCategory = Literal[
    "Student Builder",
    "Entry-Level Engineer",
    "Professional Developer",
    "Senior Engineer",
    "OSS Contributor",
    "Indie Hacker",
]


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
    commit_dates: list[datetime]
    account_created_at: datetime


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
    category: DeveloperCategory
    breakdown: ScoreBreakdown
    total: int = Field(ge=0, le=100)
    generated_at: datetime
