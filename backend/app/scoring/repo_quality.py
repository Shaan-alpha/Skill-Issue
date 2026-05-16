from datetime import UTC, datetime, timedelta

from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result

MAX_POINTS = 30
NINETY_DAYS = timedelta(days=90)
NON_DEPLOYMENT_HINTS = {"pinned"}


def score(profile: Profile) -> ScoreResult:
    non_fork = [repo for repo in profile.repos if not repo.is_fork]
    evidence: list[Evidence] = []
    points = 0

    if non_fork:
        readme_ratio = sum(1 for repo in non_fork if repo.has_readme) / len(non_fork)
        if readme_ratio >= 0.5:
            evidence.append(
                Evidence(
                    signal="readme_majority",
                    detail=f"{readme_ratio:.0%} of non-fork repos have READMEs",
                    weight=6,
                )
            )
            points += 6

    if any(repo.has_tests or repo.has_ci for repo in non_fork):
        evidence.append(
            Evidence(
                signal="testing_or_ci",
                detail="At least one non-fork repo has tests or CI",
                weight=8,
            )
        )
        points += 8

    if any(set(repo.deployment_hints) - NON_DEPLOYMENT_HINTS for repo in non_fork):
        evidence.append(
            Evidence(
                signal="deployment_hint",
                detail="Deployment artifacts are present",
                weight=6,
            )
        )
        points += 6

    now = datetime.now(UTC)
    if any(
        repo.last_commit_at is not None and now - repo.last_commit_at <= NINETY_DAYS
        for repo in non_fork
    ):
        evidence.append(
            Evidence(
                signal="recent_activity",
                detail="At least one non-fork repo has commits in the last 90 days",
                weight=6,
            )
        )
        points += 6

    if non_fork:
        licensed = sum(1 for r in non_fork if r.full_name in profile.licensed_repos)
        if licensed / len(non_fork) >= 0.5:
            evidence.append(
                Evidence(
                    signal="license_majority",
                    detail=f"{licensed}/{len(non_fork)} non-fork repos carry a recognised SPDX license",
                    weight=4,
                )
            )
            points += 4

    return make_result(points=points, max_points=MAX_POINTS, evidence=evidence)
