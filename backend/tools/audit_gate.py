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
import re

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

    if ecosystem == "pip":
        # pip-audit's shape varies by version: modern emits
        # {"dependencies": [...]}, older emits a bare array.
        if isinstance(doc, list):
            return {"dependencies": doc}
        if isinstance(doc, dict) and isinstance(doc.get("dependencies"), list):
            return doc
        return None

    raise ValueError(f"unknown ecosystem: {ecosystem}")


def _has_findings(doc: dict, ecosystem: str, threshold: str) -> bool:
    if ecosystem == "npm":
        counts = doc["metadata"]["vulnerabilities"]
        floor = SEVERITY_ORDER.index(threshold)
        return any(int(counts.get(sev, 0)) > 0 for sev in SEVERITY_ORDER[floor:])
    # pip-audit reports no severity, so `threshold` does not apply here —
    # any vulnerability at all is a finding.
    return any(dep.get("vulns") for dep in doc["dependencies"])


# Only these positively-identified failures are forgiven. Anything else
# unexplained must fail — see the ERROR verdict.
_TRANSPORT_SIGNATURES = (
    "audit endpoint returned an error",
    "invalid json response body",
    "connectionerror",
    "serviceerror",
    "socket hang up",
    "network error",
    "getaddrinfo",
    "etimedout",
    "econnreset",
    "econnrefused",
    "enotfound",
    "eai_again",
    "too many requests",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "internal server error",
)

# Matches "HTTP 503", "status code 429" — but not a bare "500" that could
# just as easily be a version number or a dependency count.
_HTTP_ERROR_RE = re.compile(r"(?:http|status(?:\s+code)?)\D{0,3}(?:429|50[0-4])", re.IGNORECASE)


def _looks_like_transport_failure(stdout: str, stderr: str) -> bool:
    blob = f"{stdout or ''}\n{stderr or ''}".lower()
    if any(sig in blob for sig in _TRANSPORT_SIGNATURES):
        return True
    return bool(_HTTP_ERROR_RE.search(blob))


def classify(stdout: str, stderr: str, ecosystem: str, threshold: str = "critical") -> str:
    """Classify one audit run. Pure — no network, no clock, no subprocess."""
    doc = _parse_results(stdout, ecosystem)
    if doc is not None:
        return FINDINGS if _has_findings(doc, ecosystem, threshold) else CLEAN
    if _looks_like_transport_failure(stdout, stderr):
        return SERVICE_UNAVAILABLE
    return ERROR
