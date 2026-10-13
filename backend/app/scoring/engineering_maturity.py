from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result
from app.scoring.commit_quality import commit_quality

MAX_POINTS = 20
# Fewer judged subjects than this says more about the sample than the habit.
_MIN_SUBJECTS_JUDGED = 10
_MANIFESTS_LISTED = 4

# Exact GitHub Linguist names. A language counts when compile-time type checking
# is mandatory or the ecosystem default (2026-10-13 research). Python is a
# deliberate exception, for its type-hint ecosystem; languages whose typing is
# opt-in (Elixir, Julia, Groovy, Luau) stay out. GitHub reports a language's
# Linguist group (Fortran Free Form as Fortran, Lean 4 as Lean, TSX as
# TypeScript), so a group's name covers its members.
TYPED_LANGUAGES = {
    "TypeScript",
    "Python",
    "Go",
    "Rust",
    "Java",
    "Kotlin",
    "Swift",
    "C#",
    "C++",
    "C",
    "Objective-C",
    "Objective-C++",
    "Dart",
    "Scala",
    "Haskell",
    "Zig",
    "OCaml",
    "F#",
    "Elm",
    "Gleam",
    "Crystal",
    "Nim",
    "D",
    "Fortran",
    "Ada",
    "Solidity",
    "Apex",
    "Visual Basic .NET",
    "Pascal",
    "Hack",
    "PureScript",
    "ReScript",
    "Reason",
    "Haxe",
    "Vala",
    "V",
    "Odin",
    "Mojo",
    "Idris",
    "Lean",
    "Move",
    "Cairo",
    "Standard ML",
    "Agda",
    "Chapel",
    "Ballerina",
}


def score(profile: Profile) -> ScoreResult:
    non_fork = [r for r in profile.repos if not r.is_fork]
    evidence: list[Evidence] = []
    points = 0

    if non_fork:
        # >= 1 typed-language repo
        if any(r.primary_language in TYPED_LANGUAGES for r in non_fork):
            evidence.append(
                Evidence(
                    signal="typed_language",
                    detail="Uses statically typed or strictly typed languages",
                    weight=4,
                )
            )
            points += 4

        # Language diversity >= 2 (with each at least 5% of total bytes)
        total_bytes = sum(profile.languages.values())
        if total_bytes > 0:
            significant_langs = [
                lang for lang, b in profile.languages.items() if b / total_bytes >= 0.05
            ]
            if len(significant_langs) >= 2:
                evidence.append(
                    Evidence(
                        signal="language_diversity",
                        detail="Writes in multiple languages significantly",
                        weight=4,
                    )
                )
                points += 4

        # >= 1 repo with multi-folder structure inferred from repo size > 200KB
        if any(r.size_kb > 200 for r in non_fork):
            evidence.append(
                Evidence(
                    signal="multi_folder_structure",
                    detail="Builds substantial repositories (>200KB)",
                    weight=4,
                )
            )
            points += 4

        # >= 3 repos with CI config
        if sum(1 for r in non_fork if r.has_ci) >= 3:
            total_workflows = (
                sum(profile.workflow_counts.values()) if profile.workflow_counts else 0
            )
            detail = (
                f"Configures CI pipelines routinely — {total_workflows} workflows across top repos"
                if total_workflows
                else "Configures CI pipelines routinely"
            )
            evidence.append(Evidence(signal="ci_culture", detail=detail, weight=4))
            points += 4

        # >= 1 repo with deployment hint AND tests
        if any(r.deployment_hints and r.has_tests for r in non_fork):
            evidence.append(
                Evidence(
                    signal="production_ready",
                    detail="Pairs testing with deployment artifacts",
                    weight=4,
                )
            )
            points += 4

        # Context rows (no points), from data ingestion already has.
        repos_with_manifests = [r for r in non_fork if r.manifests]
        if repos_with_manifests:
            kinds = sorted({m for r in repos_with_manifests for m in r.manifests}, key=str.lower)
            listed = ", ".join(kinds[:_MANIFESTS_LISTED])
            if len(kinds) > _MANIFESTS_LISTED:
                listed += f" and {len(kinds) - _MANIFESTS_LISTED} more"
            count = len(repos_with_manifests)
            evidence.append(
                Evidence(
                    signal="dependency_hygiene",
                    detail=f"Dependency manifests in {count} {'repo' if count == 1 else 'repos'}: "
                    f"{listed}",
                    weight=0,
                )
            )

    quality = commit_quality(profile.commit_subjects)
    if quality is not None and quality[1] >= _MIN_SUBJECTS_JUDGED:
        percent, judged = quality
        evidence.append(
            Evidence(
                signal="commit_quality",
                detail=(
                    f"{percent}% of {judged} commit subjects are specific and fit in 72 characters"
                ),
                weight=0,
            )
        )

    return make_result(points=points, max_points=MAX_POINTS, evidence=evidence)
