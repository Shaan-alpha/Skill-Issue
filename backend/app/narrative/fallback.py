from typing import Literal

from app.models import Report


def fallback_narrative(mode: Literal["roast", "mentor"], report: Report) -> str:
    """Deterministic on-voice templates used when OpenAI daily budget is exhausted or upstream fails."""
    badges = len(report.badges)
    badge_word = "badge" if badges == 1 else "badges"

    if mode == "roast":
        return (
            f"[AI narrator offline — daily cap reached]\n\n"
            f"GitHub confirms you sit squarely in {report.tier.name} territory with "
            f"{report.total} points across our telemetry and {badges} {badge_word}. "
            f"Your repository quality and consistency metrics are real facts recorded on the ledger. "
            f"When our AI quota resets at midnight UTC, come back to hear exactly what your commit history really says about your work habits."
        )

    return (
        f"[AI narrator offline — daily cap reached]\n\n"
        f"You have secured a solid footing as a {report.tier.name} ({report.total}/100 pts) "
        f"with {badges} {badge_word} in your portfolio. Your foundational engineering "
        f"signals remain deterministic and intact. Check back after midnight UTC when our live narrator "
        f"comes back online for targeted next steps to elevate your profile into the next tier."
    )
