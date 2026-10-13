from app.models import Evidence, Profile, ScoreResult
from app.scoring.base import make_result

MAX_POINTS = 20

# Exact GitHub Linguist names. A language counts when compile-time type checking
# is mandatory or the ecosystem default (2026-10-13 research). Python is a
# deliberate exception, for its type-hint ecosystem; languages whose typing is
# opt-in (Elixir, Julia, Groovy, Luau) stay out.
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

    return make_result(points=points, max_points=MAX_POINTS, evidence=evidence)
