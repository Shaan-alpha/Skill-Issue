from __future__ import annotations

from app.ratelimit_fallback import InProcessRateLimiter


def test_in_process_limiter_allows_under_and_denies_over():
    lim = InProcessRateLimiter()
    for _ in range(3):
        assert (
            lim.check(name="analyze", subject="ip:1.2.3.4", limit=3, bucket="2026-07-24-10") is True
        )
    # 4th over the cap
    assert lim.check(name="analyze", subject="ip:1.2.3.4", limit=3, bucket="2026-07-24-10") is False


def test_in_process_limiter_separate_buckets_and_subjects():
    lim = InProcessRateLimiter()
    assert lim.check(name="analyze", subject="ip:a", limit=1, bucket="b1") is True
    assert lim.check(name="analyze", subject="ip:a", limit=1, bucket="b1") is False
    # different subject and different bucket are independent
    assert lim.check(name="analyze", subject="ip:b", limit=1, bucket="b1") is True
    assert lim.check(name="analyze", subject="ip:a", limit=1, bucket="b2") is True
