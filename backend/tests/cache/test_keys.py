import pytest

from app.cache.keys import (
    NAMESPACE_BUDGET,
    NAMESPACE_GH,
    NAMESPACE_LOCK,
    NAMESPACE_NARRATIVE,
    NAMESPACE_REPORT,
    TTL_BUDGET_KEY_SECONDS,
    TTL_LOCK_SECONDS,
    TTL_NARRATIVE_SECONDS,
    TTL_REPORT_SECONDS,
    budget_day_key,
    gh_request_key,
    narrative_key,
    report_key,
    ttl_for_gh_endpoint,
)


def test_report_key_is_lowercased() -> None:
    """GitHub logins are case-insensitive in URLs — a key for Shaan-alpha and
    shaan-alpha must hit the same cache entry."""
    assert report_key("Shaan-alpha") == report_key("shaan-alpha") == "v1:shaan-alpha"


def test_report_key_includes_schema_version() -> None:
    """v0.9.1: Report cache keys carry a REPORT_SCHEMA_VERSION prefix so a
    future Report-shape change can invalidate the report namespace cleanly
    without nuking GH/narrative/lock/budget keys via a global KEY_PREFIX bump."""
    assert report_key("Octocat") == "v1:octocat"


def test_report_key_bump_rewrites_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bumping REPORT_SCHEMA_VERSION must change every report_key output for
    the same username — that's the whole point of the constant."""
    from app.cache import keys as keys_module

    monkeypatch.setattr(keys_module, "REPORT_SCHEMA_VERSION", 7)
    assert report_key("octocat") == "v7:octocat"


def test_narrative_key_includes_mode_and_hash() -> None:
    assert narrative_key("octocat", "abcdef0123456789", "roast") == (
        "octocat:abcdef0123456789:roast"
    )


def test_budget_day_key_uses_utc_date() -> None:
    from datetime import UTC, datetime

    fixed = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    assert budget_day_key("narrative", fixed) == "narrative:2026-05-19"


def test_gh_request_key_is_stable_across_param_ordering() -> None:
    a = gh_request_key(
        "GET",
        "https://api.github.com/users/octocat",
        {"per_page": 30, "sort": "updated"},
        None,
    )
    b = gh_request_key(
        "GET",
        "https://api.github.com/users/octocat",
        {"sort": "updated", "per_page": 30},
        None,
    )
    assert a == b


def test_gh_request_key_differs_for_different_urls() -> None:
    a = gh_request_key("GET", "https://api.github.com/users/octocat", None, None)
    b = gh_request_key("GET", "https://api.github.com/users/torvalds", None, None)
    assert a != b


def test_gh_request_key_differs_for_post_body() -> None:
    a = gh_request_key("POST", "https://api.github.com/graphql", None, {"query": "{ a }"})
    b = gh_request_key("POST", "https://api.github.com/graphql", None, {"query": "{ b }"})
    assert a != b


def test_ttl_for_gh_endpoint_users() -> None:
    assert ttl_for_gh_endpoint("https://api.github.com/users/octocat") == 3600


def test_ttl_for_gh_endpoint_repos_list() -> None:
    assert ttl_for_gh_endpoint("https://api.github.com/users/octocat/repos") == 900


def test_ttl_for_gh_endpoint_languages() -> None:
    assert ttl_for_gh_endpoint("https://api.github.com/repos/foo/bar/languages") == 3600


def test_ttl_for_gh_endpoint_contents() -> None:
    assert ttl_for_gh_endpoint("https://api.github.com/repos/foo/bar/contents/") == 1800


def test_ttl_for_gh_endpoint_commits() -> None:
    assert ttl_for_gh_endpoint("https://api.github.com/repos/foo/bar/commits") == 300


def test_ttl_for_gh_endpoint_graphql() -> None:
    assert ttl_for_gh_endpoint("https://api.github.com/graphql") == 900


def test_ttl_for_gh_endpoint_unknown_returns_none() -> None:
    """Unknown endpoint => no per-endpoint match => caller decides what to do."""
    assert ttl_for_gh_endpoint("https://api.github.com/some/new/endpoint") is None


def test_namespace_constants_are_distinct() -> None:
    """Sanity check — namespaces must not collide."""
    assert (
        len(
            {
                NAMESPACE_REPORT,
                NAMESPACE_LOCK,
                NAMESPACE_GH,
                NAMESPACE_NARRATIVE,
                NAMESPACE_BUDGET,
            }
        )
        == 5
    )


def test_ttl_constants_are_positive() -> None:
    assert TTL_REPORT_SECONDS > 0
    assert TTL_LOCK_SECONDS > 0
    assert TTL_NARRATIVE_SECONDS > 0
    assert TTL_BUDGET_KEY_SECONDS > 0
