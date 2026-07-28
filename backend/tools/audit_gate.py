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

import argparse
import json
import re
import shutil
import subprocess
import sys
import time

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


_BACKOFF_SECONDS = [5, 15]


def _run_audit(ecosystem: str, requirements: str | None) -> tuple[str, str]:
    """Shell out to the ecosystem's auditor, always requesting JSON."""
    if ecosystem == "npm":
        cmd = ["npm", "audit", "--omit=dev", "--json"]
    else:
        cmd = ["uvx", "pip-audit", "-r", str(requirements), "-f", "json"]

    # Resolve through PATH ourselves: on Windows these ship as `npm.cmd` /
    # `uvx.exe`, which CreateProcess won't find from the bare name. Falling
    # back to the bare name keeps the failure below identical on POSIX.
    cmd[0] = shutil.which(cmd[0]) or cmd[0]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        # A missing or unrunnable auditor is not a transport failure, so this
        # text carries no transport signature and classify() returns ERROR —
        # the gate fails, with a diagnostic instead of a traceback.
        return "", f"could not run {cmd[0]}: {exc}"
    return proc.stdout, proc.stderr


def run_gate(
    ecosystem: str,
    threshold: str = "critical",
    requirements: str | None = None,
    attempts: int = 3,
    sleep=time.sleep,
    runner=None,
) -> int:
    """Run the audit, retrying only on a positively-identified outage."""
    runner = runner or _run_audit

    for attempt in range(1, attempts + 1):
        stdout, stderr = runner(ecosystem, requirements)
        verdict = classify(stdout, stderr, ecosystem, threshold)

        if verdict == CLEAN:
            print(f"{ecosystem} audit clean (threshold: {threshold}).")
            return 0
        if verdict == FINDINGS:
            print(f"{ecosystem} audit found advisories at or above '{threshold}':")
            print(stdout.strip()[:4000])
            return 1
        if verdict == ERROR:
            print(f"{ecosystem} audit failed for an unrecognised reason — failing the gate.")
            print(f"--- stdout ---\n{stdout.strip()[:2000]}")
            print(f"--- stderr ---\n{stderr.strip()[:2000]}")
            return 1

        if attempt < attempts:
            delay = _BACKOFF_SECONDS[min(attempt - 1, len(_BACKOFF_SECONDS) - 1)]
            print(
                f"{ecosystem} advisory service unavailable "
                f"(attempt {attempt}/{attempts}); retrying in {delay}s."
            )
            sleep(delay)

    print(
        f"::warning::{ecosystem} audit SKIPPED — the advisory service was unreachable "
        f"after {attempts} attempts. Dependencies were NOT checked for this run."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CI audit gate.")
    parser.add_argument("ecosystem", choices=["npm", "pip"])
    parser.add_argument("--threshold", default="critical", choices=SEVERITY_ORDER)
    parser.add_argument("--requirements", help="Requirements file (pip only).")
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(argv)

    if args.ecosystem == "pip" and not args.requirements:
        parser.error("--requirements is required for the pip ecosystem")

    return run_gate(args.ecosystem, args.threshold, args.requirements, args.attempts)


if __name__ == "__main__":
    sys.exit(main())
