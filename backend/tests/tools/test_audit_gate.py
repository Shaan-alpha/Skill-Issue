from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.audit_gate import (
    CLEAN,
    ERROR,
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


PIP_CONNECTION_ERROR = (
    "ERROR:pip_audit._cli:ConnectionError: Failed to reach the OSV vulnerability service"
)


def _pip_report(*deps: dict) -> str:
    """pip-audit's modern shape: {"dependencies": [...]}."""
    return json.dumps({"dependencies": list(deps)})


def test_pip_connection_error_is_service_unavailable():
    """Case 6 — pip-audit raises ConnectionError when OSV/PyPI is unreachable."""
    assert classify("", PIP_CONNECTION_ERROR, "pip") == SERVICE_UNAVAILABLE


def test_pip_clean_report_is_clean():
    """Case 7."""
    payload = _pip_report(
        {"name": "fastapi", "version": "0.115.0", "vulns": []},
        {"name": "httpx", "version": "0.27.0", "vulns": []},
    )
    assert classify(payload, "", "pip") == CLEAN


def test_pip_legacy_bare_array_shape_is_parsed():
    """Case 8 — older pip-audit emits a bare array; both shapes must work."""
    payload = json.dumps([{"name": "httpx", "version": "0.27.0", "vulns": []}])
    assert classify(payload, "", "pip") == CLEAN


def test_pip_report_with_vulns_is_findings():
    """Case 9 — pip-audit carries no severity, so any vuln is a finding."""
    payload = _pip_report(
        {"name": "flask", "version": "0.5", "vulns": [{"id": "PYSEC-2019-179"}]},
        {"name": "httpx", "version": "0.27.0", "vulns": []},
    )
    assert classify(payload, "", "pip") == FINDINGS


@pytest.mark.parametrize("ecosystem", ["npm", "pip"])
def test_unparseable_output_without_transport_signature_is_error(ecosystem):
    """Case 10 — a crashed tool must fail loudly, not pass as an outage."""
    stdout = 'Traceback (most recent call last):\n  File "x.py", line 1\nKeyError: \'deps\''
    stderr = "invalid requirement on line 4 of requirements.txt"

    assert classify(stdout, stderr, ecosystem) == ERROR


@pytest.mark.parametrize("ecosystem", ["npm", "pip"])
def test_empty_output_without_transport_signature_is_error(ecosystem):
    """Case 11 — silence is not success."""
    assert classify("", "", ecosystem) == ERROR


@pytest.mark.parametrize(
    "stderr",
    [
        "npm error audit endpoint returned an error",
        "npm warn audit invalid json response body at https://registry.npmjs.org",
        "ConnectionError: OSV unreachable",
        "pip_audit ServiceError: PyPI returned an error",
        "request failed, reason: getaddrinfo ENOTFOUND registry.npmjs.org",
        "FetchError: request to https://registry.npmjs.org failed, reason: ETIMEDOUT",
        "Received HTTP 503 from the advisory service",
        "server responded with status code 429",
    ],
)
def test_known_transport_signatures_are_service_unavailable(stderr):
    """Each forgiven failure mode must be positively identified."""
    assert classify("", stderr, "npm") == SERVICE_UNAVAILABLE
