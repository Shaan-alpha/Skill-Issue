import pathlib

from app.models import Profile
from app.scoring.oss_collab import MAX_POINTS, score


def _load(name: str) -> Profile:
    return Profile.model_validate_json(
        (pathlib.Path(__file__).parent.parent / "fixtures" / name).read_text()
    )


def test_student_profile_scores_zero() -> None:
    profile = _load("profile_student.json")
    result = score(profile)
    assert result.points == 0
    assert result.max_points == MAX_POINTS


def test_oss_profile_scores_high() -> None:
    profile = _load("profile_oss.json")
    # ensure it has the necessary fields
    profile.external_prs_merged = 12
    profile.external_reviews = 5
    profile.external_orgs = {"facebook", "google", "microsoft"}

    result = score(profile)
    assert result.points == 15
    assert len(result.evidence) == 3


def test_senior_profile_scores_mid() -> None:
    profile = _load("profile_senior.json")
    profile.external_prs_merged = 2
    profile.external_reviews = 1
    profile.external_orgs = {"some-org"}

    result = score(profile)
    assert result.points == 8  # 5 (PRs) + 3 (Reviews) + 0 (Org diversity)
    assert len(result.evidence) == 2


def test_oss_collab_appends_review_depth_evidence_when_available() -> None:
    profile = _load("profile_oss.json")
    profile.review_avg_comments = 320
    result = score(profile)
    assert any(e.signal == "review_depth" for e in result.evidence)
