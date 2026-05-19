from typing import Literal

from app.models import Report

Mode = Literal["roast", "mentor"]
Reason = Literal["budget", "error"]

_HEADER_BY_REASON: dict[Reason, str] = {
    "budget": "[AI narrator offline — daily cap reached]",
    "error": "[AI narrator offline — upstream hiccup]",
}


def fallback_narrative(mode: Mode, report: Report, reason: Reason = "budget") -> str:
    """Deterministic on-voice templates used when the LLM is unavailable.

    `reason="budget"` covers the daily-cap path (resets at midnight UTC).
    `reason="error"` covers transient upstream failures (provider 5xx, network).
    """
    badges = len(report.badges)
    badge_word = "badge" if badges == 1 else "badges"
    header = _HEADER_BY_REASON[reason]
    retry_hint = (
        "When our AI quota resets at midnight UTC, come back"
        if reason == "budget"
        else "Refresh the page in a moment to retry"
    )
    retry_hint_mentor = (
        "Check back after midnight UTC when our live narrator comes back online"
        if reason == "budget"
        else "Refresh in a moment — the live narrator should be back shortly"
    )

    if mode == "roast":
        return (
            f"{header}\n\n"
            f"GitHub confirms you sit squarely in {report.tier.name} territory with "
            f"{report.total} points across our telemetry and {badges} {badge_word}. "
            f"Your repository quality and consistency metrics are real facts recorded on the ledger. "
            f"{retry_hint} to hear exactly what your commit history really says about your work habits."
        )

    return (
        f"{header}\n\n"
        f"You have secured a solid footing as a {report.tier.name} ({report.total}/100 pts) "
        f"with {badges} {badge_word} in your portfolio. Your foundational engineering "
        f"signals remain deterministic and intact. {retry_hint_mentor} "
        f"for targeted next steps to elevate your profile into the next tier."
    )
