"""Commit-subject quality. The old heuristic counted a subject as good when it
was at least 50 characters long, which inverts git's own guidance (50 is the
target maximum, 72 the hard limit). Rules from the 2026-10-13 research."""

import pytest

from app.scoring.commit_quality import commit_quality, is_descriptive


@pytest.mark.parametrize(
    "subject",
    [
        "Fix off-by-one in pagination cursor",
        "Add retry budget to the GitHub client",
        "feat(api)!: drop the v1 endpoints",
        "fix: handle a null avatar URL",
        "mm/slub: fix freelist corruption on resize",
    ],
)
def test_a_specific_concise_subject_is_descriptive(subject: str) -> None:
    assert is_descriptive(subject) is True


@pytest.mark.parametrize(
    "subject",
    [
        "wip",
        "fix",
        "update",
        "fix bug",
        "Small changes",
        "chore: update",
        "fix: x",
        "wip: halfway through the refactor",
        "Update README.md",
        "Add files via upload",
        "asdf asdf asdf",
        "......... .........",
        "Rewrite the entire ingestion layer so every call runs in parallel and is bounded",
    ],
)
def test_a_vague_or_rambling_subject_is_not(subject: str) -> None:
    assert is_descriptive(subject) is False


@pytest.mark.parametrize(
    "subject",
    [
        "Merge pull request #12 from octocat/feature",
        "Merge branch 'main' into feature",
        'Revert "Add retry budget"',
        "fixup! Add retry budget",
        "Initial commit",
        # The same subjects typed by hand say no more about the author.
        "initial commit",
        "merge branch 'main' into feature",
        'revert "Add retry budget"',
    ],
)
def test_tool_generated_subjects_are_not_judged(subject: str) -> None:
    assert is_descriptive(subject) is None


def test_quality_is_the_share_of_judged_subjects() -> None:
    subjects = [
        "Fix off-by-one in pagination cursor",
        "wip",
        "Merge pull request #1 from a/b",
        "Add retry budget to the GitHub client",
        "update",
    ]
    assert commit_quality(subjects) == (50, 4)


def test_nothing_to_judge_gives_no_verdict() -> None:
    assert commit_quality(["Merge branch 'main'", "Initial commit"]) is None
    assert commit_quality([]) is None


def test_a_pathological_subject_is_judged_without_a_crash() -> None:
    """Commit messages are attacker-influenced (anyone can analyze a crafted repo)."""
    huge = "feat(" + "a" * 10_000 + "): " + "z" * 100_000
    assert is_descriptive(huge) is False
