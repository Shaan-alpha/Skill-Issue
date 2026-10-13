"""Commit-subject quality, judged by git's own guidance.

git-commit(1) asks for "a single short (no more than 50 characters) line"; 72
is the common hard limit, past which GitHub truncates the subject. No source
sets a minimum, so a subject is judged on being specific and concise: at
least two words of real description, and not one of the low-information
placeholders. Subjects tools write (merges, reverts, fixups, the initial
commit) say nothing about the author and are left out. Rules from the
2026-10-13 research; the 10-character and two-word floors are design choices.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

# Case-insensitive: typed by hand, these subjects say no more about the author.
_TOOL_GENERATED = re.compile(
    r"^(?:Merge (?:pull request|branch|remote-tracking branch|tag)\b"
    r'|Revert "|Reapply "|(?:fixup|squash|amend)! |Initial commit$)',
    re.IGNORECASE,
)
# A Conventional Commits header or a git/kernel "area: " prefix. The
# description is what gets judged.
_PREFIXED = re.compile(
    r"^(?P<type>[a-z][\w./-]*)(?:\([^()\r\n]+\))?!?: (?P<desc>\S.*)$", re.IGNORECASE
)
# GitHub's web-editor defaults ("Update README.md", "Add files via upload").
_WEB_EDITOR_DEFAULT = re.compile(
    r"^(?:(?:update|create|delete|rename|add) [\w./-]+\.\w{1,6}|add files via upload)$",
    re.IGNORECASE,
)
_LOW_INFORMATION = frozenset(
    {
        "wip",
        "update",
        "updates",
        "updated",
        "fix",
        "fixes",
        "fixed",
        "fix bug",
        "fix bugs",
        "bug fix",
        "bugfix",
        "fix stuff",
        "changes",
        "change",
        "small changes",
        "minor",
        "minor changes",
        "minor fix",
        "minor fixes",
        "misc",
        "stuff",
        "test",
        "tests",
        "testing",
        "tmp",
        "temp",
        "cleanup",
        "clean up",
        "refactor",
        "edit",
        "edits",
        "save",
        "commit",
        "asdf",
        "init",
        "initial",
        "first commit",
        "more",
        "done",
        "final",
        "oops",
        "typo",
        "fix typo",
        "work in progress",
    }
)
_SUBJECT_MIN, _SUBJECT_MAX = 10, 72


def is_descriptive(subject: str) -> bool | None:
    """Whether a commit subject is specific and concise; None when a tool
    wrote it and it says nothing about the author."""
    subject = subject.strip()
    if _TOOL_GENERATED.match(subject):
        return None
    prefixed = _PREFIXED.match(subject)
    if prefixed and prefixed.group("type").lower() == "wip":
        return False
    description = prefixed.group("desc") if prefixed else subject
    words = description.split()
    return (
        _SUBJECT_MIN <= len(subject) <= _SUBJECT_MAX
        and len(words) >= 2
        and len(set(w.lower() for w in words)) > 1
        and description.lower().rstrip(".!?…") not in _LOW_INFORMATION
        and any(char.isalpha() for char in description)
        and not _WEB_EDITOR_DEFAULT.match(subject)
    )


def commit_quality(subjects: Iterable[str]) -> tuple[int, int] | None:
    """(percent descriptive, subjects judged), or None when nothing was judged."""
    verdicts = [v for v in map(is_descriptive, subjects) if v is not None]
    if not verdicts:
        return None
    return round(sum(verdicts) / len(verdicts) * 100), len(verdicts)
