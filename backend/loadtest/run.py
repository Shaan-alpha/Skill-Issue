"""Open-loop load-test harness for the Skill Issue backend.

Drives a target endpoint at a fixed request rate and reports latency
percentiles, error rate, and achieved throughput against pass/fail
thresholds. See backend/loadtest/README.md for the local warm-/analyze
runbook. Run: uv run python loadtest/run.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys
import time
from dataclasses import dataclass

import httpx


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


async def _one_request(client: httpx.AsyncClient, url: str, results: list[Result]) -> None:
    t0 = time.perf_counter()
    try:
        resp = await client.get(url)
        status: int | None = resp.status_code
    except (httpx.HTTPError, OSError):
        status = None
    results.append(Result(latency_ms=(time.perf_counter() - t0) * 1000.0, status=status))


async def run_stage(
    client: httpx.AsyncClient,
    url: str,
    *,
    rps: float,
    duration: float,
    max_inflight: int,
) -> tuple[list[Result], int]:
    """Open-loop: schedule requests at a fixed rate for `duration` seconds.

    Returns (results, dropped). `dropped` counts ticks skipped because
    `max_inflight` was saturated — a "server can't keep up" signal. The
    scheduler never blocks on in-flight requests, so a slow server shows up as
    dropped ticks + latency growth rather than self-throttled load.
    """
    results: list[Result] = []
    tasks: set[asyncio.Task[None]] = set()
    inflight = 0
    dropped = 0
    interval = 1.0 / rps
    loop = asyncio.get_running_loop()

    def _done(t: asyncio.Task[None]) -> None:
        nonlocal inflight
        inflight -= 1
        tasks.discard(t)

    start = loop.time()
    i = 0
    while loop.time() - start < duration:
        delay = (start + i * interval) - loop.time()
        if delay > 0:
            await asyncio.sleep(delay)
        i += 1
        if inflight >= max_inflight:
            dropped += 1
            continue
        inflight += 1
        task = asyncio.create_task(_one_request(client, url, results))
        task.add_done_callback(_done)
        tasks.add(task)

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    return results, dropped


def _parse_ramp(ramp: str) -> list[float]:
    """'10:50:100' -> [10.0, 50.0, 100.0]."""
    return [float(part) for part in ramp.split(":") if part]


def _print_summary(url: str, rps: float, s: Summary, ok: bool, failures: list[str]) -> None:
    print(f"\n=== {url} @ target {rps:.0f} RPS for {s.duration_s:.1f}s ===")
    print(f"  sent={s.sent} completed={s.completed} dropped={s.dropped}")
    print(f"  achieved_rps={s.achieved_rps:.1f}")
    print(f"  errors={s.error_count} ({s.error_rate:.3%}) {s.errors_by_status or ''}")
    print(f"  latency p50={s.p50_ms:.1f}ms p95={s.p95_ms:.1f}ms p99={s.p99_ms:.1f}ms")
    print(f"  RESULT: {'PASS' if ok else 'FAIL'}")
    for f in failures:
        print(f"    - {f}")


async def _amain(args: argparse.Namespace) -> int:
    url = args.target.rstrip("/") + args.path
    cap = args.max_inflight + 50
    limits = httpx.Limits(max_connections=cap, max_keepalive_connections=cap)
    overall_ok = True
    async with httpx.AsyncClient(timeout=args.timeout, limits=limits) as client:
        for _ in range(args.warmup):
            with contextlib.suppress(httpx.HTTPError, OSError):
                await client.get(url)
        stages = _parse_ramp(args.ramp) if args.ramp else [args.rps]
        for rps in stages:
            wall0 = time.perf_counter()
            results, dropped = await run_stage(
                client, url, rps=rps, duration=args.duration, max_inflight=args.max_inflight
            )
            summary = summarize(results, dropped=dropped, wall_seconds=time.perf_counter() - wall0)
            ok, failures = evaluate_thresholds(
                summary,
                target_rps=rps,
                max_error_rate=args.max_error_rate,
                p95_ms=args.p95_ms,
            )
            _print_summary(url, rps, summary, ok, failures)
            overall_ok = overall_ok and ok
    return 0 if overall_ok else 1


def main() -> None:
    p = argparse.ArgumentParser(description="Open-loop load tester for the Skill Issue backend.")
    p.add_argument("--target", default="http://localhost:8000")
    p.add_argument("--path", default="/analyze/octocat")
    p.add_argument("--rps", type=float, default=100.0)
    p.add_argument("--duration", type=float, default=60.0)
    p.add_argument("--warmup", type=int, default=1)
    p.add_argument("--ramp", default=None, help="colon-separated RPS stages, e.g. 10:50:100")
    p.add_argument("--max-inflight", type=int, default=500, dest="max_inflight")
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--p95-ms", type=float, default=250.0, dest="p95_ms")
    p.add_argument("--max-error-rate", type=float, default=0.01, dest="max_error_rate")
    sys.exit(asyncio.run(_amain(p.parse_args())))


if __name__ == "__main__":
    main()
