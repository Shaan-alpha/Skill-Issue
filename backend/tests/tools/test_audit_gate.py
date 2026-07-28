from __future__ import annotations

import json
from pathlib import Path

from tools.audit_gate import (
    CLEAN,
    FINDINGS,
    SERVICE_UNAVAILABLE,
    classify,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _npm_report(**counts: int) -> str:
    """An npm audit v2 report with the given severity counts."""
    vulns = {"info": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0}
    vulns.update(counts)
    vulns["total"] = sum(vulns[k] for k in ("info", "low", "moderate", "high", "critical"))
    return json.dumps(
        {
            "auditReportVersion": 2,
            "vulnerabilities": {},
            "metadata": {
                "vulnerabilities": vulns,
                "dependencies": {"prod": 1, "dev": 0, "total": 1},
            },
        }
    )


def test_npm_outage_payload_is_service_unavailable():
    """Case 1 — the real captured payload from the 2026-07-26 npm incident."""
    stdout = (FIXTURES / "npm_outage_stdout.json").read_text(encoding="utf-8")
    stderr = (FIXTURES / "npm_outage_stderr.txt").read_text(encoding="utf-8")

    assert classify(stdout, stderr, "npm", "critical") == SERVICE_UNAVAILABLE


def test_npm_clean_report_is_clean():
    """Case 2."""
    assert classify(_npm_report(), "", "npm", "critical") == CLEAN


def test_npm_critical_vuln_at_critical_threshold_is_findings():
    """Case 3."""
    assert classify(_npm_report(critical=1), "", "npm", "critical") == FINDINGS


def test_npm_moderate_only_below_critical_threshold_is_clean():
    """Case 4 — severities under the threshold must not fail the gate."""
    assert classify(_npm_report(moderate=7), "", "npm", "critical") == CLEAN


def test_npm_high_vulns_at_high_threshold_is_findings():
    """Case 5 — proves the threshold knob, which is the deferred `high` restore path."""
    assert classify(_npm_report(high=3), "", "npm", "high") == FINDINGS
