from datetime import UTC, datetime

from app.models import (
    Evidence,
    Profile,
    Repo,
    Report,
    ScoreBreakdown,
    ScoreResult,
)


def test_evidence_holds_signal_and_weight() -> None:
    ev = Evidence(signal="has_readme", detail="README is 1200 chars", weight=5)
    assert ev.signal == "has_readme"
    assert ev.weight == 5


def test_score_result_caps_at_max_points() -> None:
    sr = ScoreResult(points=25, max_points=30, evidence=[])
    assert sr.points <= sr.max_points


def test_report_total_is_sum_of_breakdown() -> None:
    breakdown = ScoreBreakdown(
        repo_quality=ScoreResult(points=20, max_points=30, evidence=[]),
        engineering_maturity=ScoreResult(points=15, max_points=20, evidence=[]),
        oss_collab=ScoreResult(points=10, max_points=15, evidence=[]),
        consistency=ScoreResult(points=7, max_points=10, evidence=[]),
        recruiter_signal=ScoreResult(points=12, max_points=15, evidence=[]),
        learning_trajectory=ScoreResult(points=6, max_points=10, evidence=[]),
    )
    report = Report(
        username="octocat",
        category="Professional Developer",
        breakdown=breakdown,
        total=breakdown.total(),
        generated_at=datetime.now(UTC),
    )
    assert report.total == 70
    assert breakdown.total() == 70


def test_repo_minimal_fields() -> None:
    repo = Repo(
        name="hello-world",
        full_name="octocat/hello-world",
        primary_language="Python",
        stars=42,
        forks=3,
        is_fork=False,
        has_readme=True,
        has_tests=False,
        has_ci=True,
        deployment_hints=[],
        last_commit_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )
    assert repo.full_name == "octocat/hello-world"


def test_profile_assembles() -> None:
    profile = Profile(
        username="octocat",
        bio="Test user",
        profile_readme_chars=400,
        followers=10,
        public_repos=5,
        languages={"Python": 800, "TypeScript": 200},
        repos=[],
        external_prs_merged=3,
        external_reviews=2,
        commit_dates=[],
        account_created_at=datetime.now(UTC),
    )
    assert profile.username == "octocat"
