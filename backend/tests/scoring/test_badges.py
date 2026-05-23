from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.models import Profile, Repo, ScoreBreakdown, ScoreResult
from app.scoring.badges import compute_badges

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _zero_breakdown() -> ScoreBreakdown:
    z = ScoreResult(points=0, max_points=1)
    return ScoreBreakdown(
        repo_quality=z,
        engineering_maturity=z,
        oss_collab=z,
        consistency=z,
        recruiter_signal=z,
        learning_trajectory=z,
    )


def _profile(name: str = "profile_student.json") -> Profile:
    return Profile.model_validate_json((FIXTURES / name).read_text())


def test_no_badges_for_empty_profile() -> None:
    profile = _profile()  # student fixture, no notable signals
    badges = compute_badges(profile, _zero_breakdown())
    assert badges == []


def _profile_with_external(prs: int, reviews: int, orgs: int = 0) -> Profile:
    p = _profile()
    p.external_prs_merged = prs
    p.external_reviews = reviews
    p.external_orgs = {f"org-{i}" for i in range(orgs)}
    return p


def test_oss_contributor_threshold() -> None:
    assert any(
        b.slug == "oss-contributor"
        for b in compute_badges(_profile_with_external(10, 0, 2), _zero_breakdown())
    )
    assert not any(
        b.slug == "oss-contributor"
        for b in compute_badges(_profile_with_external(9, 0, 2), _zero_breakdown())
    )


def test_pr_master_threshold() -> None:
    assert any(
        b.slug == "pr-master"
        for b in compute_badges(_profile_with_external(50, 0, 2), _zero_breakdown())
    )
    assert not any(
        b.slug == "pr-master"
        for b in compute_badges(_profile_with_external(49, 0, 2), _zero_breakdown())
    )


def test_maintainer_threshold() -> None:
    assert any(
        b.slug == "maintainer"
        for b in compute_badges(_profile_with_external(0, 25), _zero_breakdown())
    )
    assert not any(
        b.slug == "maintainer"
        for b in compute_badges(_profile_with_external(0, 24), _zero_breakdown())
    )


def test_pr_family_stacks() -> None:
    slugs = {b.slug for b in compute_badges(_profile_with_external(60, 30, 3), _zero_breakdown())}
    assert {"oss-contributor", "pr-master", "maintainer"}.issubset(slugs)


def _make_repo(name: str, *, stars: int = 0, is_fork: bool = False) -> Repo:
    return Repo(
        name=name,
        full_name=f"u/{name}",
        primary_language="Python",
        stars=stars,
        forks=0,
        is_fork=is_fork,
        has_readme=False,
        has_tests=False,
        has_ci=False,
        deployment_hints=[],
        size_kb=10,
        last_commit_at=None,
        created_at=datetime.now(UTC),
    )


def test_star_magnet_threshold() -> None:
    p = _profile()
    p.repos = [_make_repo("alpha", stars=1000)]
    assert any(b.slug == "star-magnet" for b in compute_badges(p, _zero_breakdown()))

    p.repos = [_make_repo("alpha", stars=999)]
    assert not any(b.slug == "star-magnet" for b in compute_badges(p, _zero_breakdown()))


def test_star_magnet_ignores_forks() -> None:
    p = _profile()
    p.repos = [_make_repo("forked", stars=5000, is_fork=True)]
    assert not any(b.slug == "star-magnet" for b in compute_badges(p, _zero_breakdown()))


def test_polyglot_threshold() -> None:
    p = _profile()
    # 4 languages each ≥ 5% — 100 bytes per language, 400 total → each is 25%
    p.languages = {"Python": 100, "TypeScript": 100, "Go": 100, "Rust": 100}
    assert any(b.slug == "polyglot" for b in compute_badges(p, _zero_breakdown()))

    # 3 languages above 5% → no badge
    p.languages = {"Python": 100, "TypeScript": 100, "Go": 100, "Rust": 1}
    assert not any(b.slug == "polyglot" for b in compute_badges(p, _zero_breakdown()))


def test_long_haul_requires_age_and_recent_activity() -> None:
    p = _profile()
    p.account_created_at = datetime.now(UTC) - timedelta(days=365 * 9)
    p.commit_dates = [datetime.now(UTC) - timedelta(days=30)]
    assert any(b.slug == "long-haul" for b in compute_badges(p, _zero_breakdown()))

    # young but active
    p.account_created_at = datetime.now(UTC) - timedelta(days=365 * 5)
    assert not any(b.slug == "long-haul" for b in compute_badges(p, _zero_breakdown()))

    # old but inactive (last commit > 365 days)
    p.account_created_at = datetime.now(UTC) - timedelta(days=365 * 9)
    p.commit_dates = [datetime.now(UTC) - timedelta(days=400)]
    assert not any(b.slug == "long-haul" for b in compute_badges(p, _zero_breakdown()))


def _breakdown_with_consistency(points: int) -> ScoreBreakdown:
    b = _zero_breakdown()
    b.consistency = ScoreResult(points=points, max_points=10)
    return b


def test_indie_hacker_full_trigger() -> None:
    p = _profile()
    p.blog = "https://example.com"
    p.hireable = False
    p.company = None
    assert any(b.slug == "indie-hacker" for b in compute_badges(p, _breakdown_with_consistency(8)))


def test_indie_hacker_blocked_by_company() -> None:
    p = _profile()
    p.blog = "https://example.com"
    p.hireable = False
    p.company = "@stripe"
    assert not any(
        b.slug == "indie-hacker" for b in compute_badges(p, _breakdown_with_consistency(8))
    )


def test_indie_hacker_blocked_by_hireable_true() -> None:
    p = _profile()
    p.blog = "https://example.com"
    p.hireable = True
    p.company = None
    assert not any(
        b.slug == "indie-hacker" for b in compute_badges(p, _breakdown_with_consistency(8))
    )


def test_toolmaker_threshold() -> None:
    p = _profile()
    p.repos = [_make_repo("a", stars=200), _make_repo("b", stars=300)]
    assert any(b.slug == "toolmaker" for b in compute_badges(p, _zero_breakdown()))

    p.repos = [_make_repo("a", stars=200), _make_repo("b", stars=199)]
    assert not any(b.slug == "toolmaker" for b in compute_badges(p, _zero_breakdown()))
