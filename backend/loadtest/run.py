"""Open-loop load-test harness for the Skill Issue backend.

Drives a target endpoint at a fixed request rate and reports latency
percentiles, error rate, and achieved throughput against pass/fail
thresholds. See backend/loadtest/README.md for the local warm-/analyze
runbook. Run: uv run python loadtest/run.py --help
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Result:
    latency_ms: float
    status: int | None  # None = connection error / timeout


@dataclass
class Summary:
    sent: int
    completed: int
    dropped: int
    error_count: int
    error_rate: float
    achieved_rps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    errors_by_status: dict[str, int]
    duration_s: float


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolated p-th percentile (p in [0, 100]). 0.0 for empty input."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    frac = k - lo
    return round(s[lo] * (1 - frac) + s[hi] * frac, 10)


def summarize(results: list[Result], *, dropped: int, wall_seconds: float) -> Summary:
    completed = len(results)
    latencies = [r.latency_ms for r in results]
    errors_by_status: dict[str, int] = {}
    error_count = 0
    for r in results:
        if r.status is None or r.status >= 400:
            key = "connection_error" if r.status is None else str(r.status)
            errors_by_status[key] = errors_by_status.get(key, 0) + 1
            error_count += 1
    error_rate = (error_count / completed) if completed else 1.0
    achieved_rps = (completed / wall_seconds) if wall_seconds > 0 else 0.0
    return Summary(
        sent=completed + dropped,
        completed=completed,
        dropped=dropped,
        error_count=error_count,
        error_rate=error_rate,
        achieved_rps=achieved_rps,
        p50_ms=percentile(latencies, 50),
        p95_ms=percentile(latencies, 95),
        p99_ms=percentile(latencies, 99),
        errors_by_status=errors_by_status,
        duration_s=wall_seconds,
    )


def evaluate_thresholds(
    summary: Summary, *, target_rps: float, max_error_rate: float, p95_ms: float
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if summary.error_rate > max_error_rate:
        failures.append(f"error rate {summary.error_rate:.3%} > {max_error_rate:.3%}")
    if summary.achieved_rps < target_rps * 0.95:
        failures.append(f"achieved RPS {summary.achieved_rps:.1f} < 95% of target {target_rps:.0f}")
    if summary.p95_ms > p95_ms:
        failures.append(f"p95 {summary.p95_ms:.1f}ms > {p95_ms:.1f}ms")
    return (not failures, failures)
