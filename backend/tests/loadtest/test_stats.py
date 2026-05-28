from loadtest.run import Result, evaluate_thresholds, percentile, summarize


def test_percentile_linear_interpolation():
    vals = [float(x) for x in range(1, 11)]  # 1..10
    assert percentile(vals, 50) == 5.5
    assert percentile(vals, 95) == 9.55
    assert percentile(vals, 99) == 9.91


def test_percentile_empty_is_zero():
    assert percentile([], 95) == 0.0


def test_percentile_single_value():
    assert percentile([7.0], 95) == 7.0


def test_summarize_counts_errors_and_rate():
    results = [
        Result(10.0, 200),
        Result(20.0, 200),
        Result(30.0, 500),
        Result(40.0, None),
    ]
    s = summarize(results, dropped=1, wall_seconds=2.0)
    assert s.completed == 4
    assert s.sent == 5
    assert s.dropped == 1
    assert s.error_count == 2
    assert s.error_rate == 0.5
    assert s.errors_by_status == {"500": 1, "connection_error": 1}
    assert s.achieved_rps == 2.0  # 4 completed / 2.0s


def test_evaluate_thresholds_all_pass():
    s = summarize([Result(10.0, 200)] * 100, dropped=0, wall_seconds=1.0)
    ok, failures = evaluate_thresholds(s, target_rps=100, max_error_rate=0.01, p95_ms=250)
    assert ok
    assert failures == []


def test_evaluate_thresholds_flags_all_three():
    s = summarize(
        [Result(500.0, 500)] * 50, dropped=0, wall_seconds=5.0
    )  # 10 rps, all errors, slow
    ok, failures = evaluate_thresholds(s, target_rps=100, max_error_rate=0.01, p95_ms=250)
    assert not ok
    assert len(failures) == 3  # error rate + achieved rps + p95
