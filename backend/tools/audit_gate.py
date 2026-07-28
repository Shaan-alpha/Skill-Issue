"""CI audit gate — tells advisory findings apart from registry outages.

Both `npm audit` and `pip-audit` exit 1 for a real advisory AND for a
transport failure, so gating on the exit code alone makes any registry
outage a repo-wide hard blocker (npm, 2026-07-26). This module classifies
on the parsed output shape instead: neither tool emits a valid results
document when the network fails.

Only positively-identified transport failures are forgiven. Anything
unexplained returns ERROR and still fails, so "pass on outage" cannot
degrade into "pass on anything we don't understand".
"""

from __future__ import annotations

import json

CLEAN = "CLEAN"
FINDINGS = "FINDINGS"
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
ERROR = "ERROR"

# npm's vocabulary, ascending. Note "moderate", not "medium".
SEVERITY_ORDER = ["info", "low", "moderate", "high", "critical"]


def _parse_results(stdout: str, ecosystem: str) -> dict | None:
    """Return the parsed results document, or None if stdout isn't one."""
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        doc = json.loads(text)
    except ValueError:
        return None

    if ecosystem == "npm":
        if not isinstance(doc, dict) or "error" in doc:
            return None
        meta = doc.get("metadata")
        if not isinstance(meta, dict) or not isinstance(meta.get("vulnerabilities"), dict):
            return None
        return doc

    raise ValueError(f"unknown ecosystem: {ecosystem}")


def _has_findings(doc: dict, ecosystem: str, threshold: str) -> bool:
    counts = doc["metadata"]["vulnerabilities"]
    floor = SEVERITY_ORDER.index(threshold)
    return any(int(counts.get(sev, 0)) > 0 for sev in SEVERITY_ORDER[floor:])


def classify(stdout: str, stderr: str, ecosystem: str, threshold: str = "critical") -> str:
    """Classify one audit run. Pure — no network, no clock, no subprocess."""
    doc = _parse_results(stdout, ecosystem)
    if doc is not None:
        return FINDINGS if _has_findings(doc, ecosystem, threshold) else CLEAN
    return SERVICE_UNAVAILABLE
