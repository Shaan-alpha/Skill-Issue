from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import audit_gate
from tools.audit_gate import (
    CLEAN,
    ERROR,
    FINDINGS,
    SERVICE_UNAVAILABLE,
    classify,
    run_gate,
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
    stdout = "Traceback (most recent call last):\n  File \"x.py\", line 1\nKeyError: 'deps'"
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


class _FakeRunner:
    """Returns a scripted (stdout, stderr) per call and counts invocations."""

    def __init__(self, *responses: tuple[str, str]):
        self._responses = list(responses)
        self.calls = 0

    def __call__(self, ecosystem: str, requirements: str | None) -> tuple[str, str]:
        self.calls += 1
        return self._responses[min(self.calls - 1, len(self._responses) - 1)]


def test_run_gate_retries_then_passes_with_warning_on_outage(capsys):
    """Case 12 — exhausted retries on a real outage exit 0, loudly."""
    outage = ("", "npm error audit endpoint returned an error")
    runner = _FakeRunner(outage)
    slept: list[int] = []

    code = run_gate("npm", attempts=3, sleep=slept.append, runner=runner)

    assert code == 0
    assert runner.calls == 3
    assert slept == [5, 15]
    assert "::warning::" in capsys.readouterr().out


def test_run_gate_recovers_if_a_retry_succeeds(capsys):
    """A transient blip resolves without a warning."""
    outage = ("", "npm error audit endpoint returned an error")
    runner = _FakeRunner(outage, (_npm_report(), ""))
    slept: list[int] = []

    code = run_gate("npm", attempts=3, sleep=slept.append, runner=runner)

    assert code == 0
    assert runner.calls == 2
    assert slept == [5]
    assert "::warning::" not in capsys.readouterr().out


def test_run_gate_does_not_retry_on_findings():
    """Case 13 — a real advisory fails fast."""
    runner = _FakeRunner((_npm_report(critical=1), ""))
    slept: list[int] = []

    code = run_gate("npm", threshold="critical", attempts=3, sleep=slept.append, runner=runner)

    assert code == 1
    assert runner.calls == 1
    assert slept == []


def test_run_gate_does_not_retry_on_error():
    """Case 14 — an unexplained failure fails fast."""
    runner = _FakeRunner(("garbage", "nothing recognisable here"))
    slept: list[int] = []

    code = run_gate("npm", attempts=3, sleep=slept.append, runner=runner)

    assert code == 1
    assert runner.calls == 1
    assert slept == []


def test_missing_auditor_binary_is_error_not_outage(monkeypatch):
    """A missing npm/uvx must fail the gate, not be forgiven as an outage.

    `_run_audit` turns the OSError into stderr text carrying no transport
    signature, so it lands on ERROR rather than escaping as a traceback.
    """
    monkeypatch.setattr(audit_gate.shutil, "which", lambda _: None)

    def _boom(*args, **kwargs):
        raise FileNotFoundError(2, "The system cannot find the file specified")

    monkeypatch.setattr(audit_gate.subprocess, "run", _boom)

    stdout, stderr = audit_gate._run_audit("npm", None)

    assert "could not run npm" in stderr
    assert classify(stdout, stderr, "npm") == ERROR
