"""Tests for the Sentry before_send PII scrub hook."""

from __future__ import annotations

import copy
import sys

import pytest

from app.observability.sentry import init_sentry, scrub_event


def test_scrub_removes_cookie_header_from_request():
    event = {
        "request": {
            "headers": {
                "Cookie": "si_session=secret",
                "User-Agent": "pytest",
            }
        }
    }
    scrubbed = scrub_event(copy.deepcopy(event), {})
    assert "Cookie" not in scrubbed["request"]["headers"]
    assert "cookie" not in {k.lower() for k in scrubbed["request"]["headers"]}
    assert scrubbed["request"]["headers"]["User-Agent"] == "pytest"


def test_scrub_removes_authorization_header():
    event = {"request": {"headers": {"Authorization": "Bearer secret-token"}}}
    scrubbed = scrub_event(copy.deepcopy(event), {})
    assert scrubbed["request"]["headers"] == {}


def test_scrub_strips_internal_and_ip_headers():
    event = {
        "request": {
            "headers": {
                "X-Internal-Secret": "supersecret",
                "X-Revalidate-Secret": "revsecret",
                "X-Client-IP": "9.9.9.9",
                "X-Forwarded-For": "9.9.9.9",
                "X-Real-IP": "9.9.9.9",
                "Accept": "application/json",
            }
        }
    }
    out = scrub_event(copy.deepcopy(event), {})
    headers = out["request"]["headers"]
    assert "Accept" in headers
    for gone in (
        "X-Internal-Secret",
        "X-Revalidate-Secret",
        "X-Client-IP",
        "X-Forwarded-For",
        "X-Real-IP",
    ):
        assert gone not in headers


def test_scrub_removes_set_cookie_response_header():
    event = {
        "extra": {
            "response_headers": {
                "Set-Cookie": "si_session=secret; Path=/; HttpOnly",
            }
        }
    }
    scrubbed = scrub_event(copy.deepcopy(event), {})
    assert "Set-Cookie" not in scrubbed["extra"]["response_headers"]


def test_scrub_removes_known_pii_fields_from_extra():
    event = {
        "extra": {
            "access_token": "gho_supersecret",
            "access_token_ct": b"\x01\x02\x03",
            "oauth_state": "state-token",
            "oauth_code": "code-token",
            "session_id": "raw-session",
            "email": "shaan@example.com",
            "innocent_field": "kept",
        }
    }
    scrubbed = scrub_event(copy.deepcopy(event), {})
    extra = scrubbed["extra"]
    for k in (
        "access_token",
        "access_token_ct",
        "oauth_state",
        "oauth_code",
        "session_id",
        "email",
    ):
        assert k not in extra, f"{k} was not scrubbed"
    assert extra["innocent_field"] == "kept"


def test_scrub_drops_user_email_when_present():
    event = {"user": {"id": "u1", "email": "user@example.com"}}
    scrubbed = scrub_event(copy.deepcopy(event), {})
    assert scrubbed["user"]["id"] == "u1"
    assert "email" not in scrubbed["user"]


def test_scrub_is_recursive_for_nested_dicts():
    event = {
        "contexts": {
            "auth": {
                "access_token": "should-be-scrubbed",
                "kept": "yes",
            }
        }
    }
    scrubbed = scrub_event(copy.deepcopy(event), {})
    assert "access_token" not in scrubbed["contexts"]["auth"]
    assert scrubbed["contexts"]["auth"]["kept"] == "yes"


def test_scrub_handles_missing_sections_gracefully():
    """Real events don't always have every section."""
    scrub_event({}, {})
    scrub_event({"message": "hi"}, {})
    scrub_event({"request": None}, {})  # must not raise


def test_init_sentry_is_noop_when_dsn_unset(monkeypatch):
    """No DSN → no init call. Code that fires later (capture_exception) is a
    no-op rather than crashing the app."""
    called: dict[str, bool] = {"init": False}

    def _fake_init(**kwargs):
        called["init"] = True

    monkeypatch.setattr("sentry_sdk.init", _fake_init)
    init_sentry(dsn=None, environment="test", traces_sample_rate=0.1, release="0.8.0")
    assert called["init"] is False


def test_init_sentry_calls_sdk_when_dsn_set(monkeypatch):
    captured: dict = {}

    def _fake_init(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("sentry_sdk.init", _fake_init)
    init_sentry(
        dsn="https://abc@o123.ingest.sentry.io/456",
        environment="production",
        traces_sample_rate=0.25,
        release="0.8.0",
    )
    assert captured["dsn"] == "https://abc@o123.ingest.sentry.io/456"
    assert captured["environment"] == "production"
    assert captured["traces_sample_rate"] == 0.25
    assert captured["release"] == "0.8.0"
    assert callable(captured["before_send"])


def test_init_sentry_keeps_the_sdk_default_of_no_pii(monkeypatch):
    """sentry-sdk 2.72 deprecates send_default_pii, even passed as False, and
    its replacement, data_collection, opts into more permissive defaults the
    moment it is passed. Passing neither keeps the SDK's conservative default."""
    captured: dict = {}
    monkeypatch.setattr("sentry_sdk.init", lambda **kwargs: captured.update(kwargs))

    init_sentry(
        dsn="https://abc@o123.ingest.sentry.io/456",
        environment="production",
        traces_sample_rate=0.25,
        release="0.8.0",
    )

    assert "send_default_pii" not in captured
    assert "data_collection" not in captured


def test_init_sentry_skips_when_already_initialised(monkeypatch):
    """A second init_sentry call should NOT create a second client."""
    init_calls: list[dict] = []

    def _fake_init(**kwargs):
        init_calls.append(kwargs)

    monkeypatch.setattr("sentry_sdk.init", _fake_init)
    monkeypatch.setattr("sentry_sdk.is_initialized", lambda: True)

    init_sentry(
        dsn="https://abc@o123.ingest.sentry.io/456",
        environment="production",
        traces_sample_rate=0.1,
        release="0.8.0",
    )
    assert init_calls == []  # second call skipped


def test_init_sentry_turns_off_the_openai_integration(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr("sentry_sdk.init", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr("sentry_sdk.is_initialized", lambda: False)

    init_sentry(
        dsn="https://abc@o123.ingest.sentry.io/456",
        environment="test",
        traces_sample_rate=0.0,
        release="0.8.0",
    )

    assert [type(i).__name__ for i in captured["disabled_integrations"]] == ["OpenAIIntegration"]


def test_sentry_still_starts_when_the_openai_integration_cannot_load(monkeypatch):
    """The integration raises at import when openai is missing or reorganised
    (openai 3 is planned); telemetry must never stop the app from starting."""
    captured: dict = {}
    monkeypatch.setattr("sentry_sdk.init", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr("sentry_sdk.is_initialized", lambda: False)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.openai", None)

    init_sentry(
        dsn="https://abc@o123.ingest.sentry.io/456",
        environment="test",
        traces_sample_rate=0.0,
        release="0.8.0",
    )

    assert captured["disabled_integrations"] == []


_FILTERED = "[Filtered]"


def test_only_allowlisted_request_headers_survive():
    event = {
        "request": {
            "headers": {
                "user-agent": "pytest",
                "referer": "https://skillissue.tech/me?code=abc&mode=roast",
                "content-type": "application/json",
                "accept": "*/*",
                "host": "skillissue.tech",
                "cookie": "si_session=s",
                "x-internal-secret": "s",
                "x-vercel-forwarded-for": "203.0.113.7",
                "x-vercel-ip-city": "Delhi",
                "x-vercel-oidc-token": "eyJ",
                "x-forwarded-host": "evil.test",
                "accept-language": "en",
            }
        }
    }
    headers = scrub_event(event, {})["request"]["headers"]
    assert headers == {
        "user-agent": "pytest",
        "referer": f"https://skillissue.tech/me?code={_FILTERED}&mode=roast",
        "content-type": "application/json",
        "accept": "*/*",
        "host": "skillissue.tech",
    }


def test_header_names_are_matched_in_any_case():
    event = {"request": {"headers": {"User-Agent": "pytest", "COOKIE": "s", "Accept": ["a", "b"]}}}
    assert scrub_event(event, {})["request"]["headers"] == {
        "User-Agent": "pytest",
        "Accept": ["a", "b"],
    }


def test_cookies_bodies_env_and_ip_never_leave():
    event = {
        "request": {
            "cookies": {"si_session": "s"},
            "data": {"a": 1},
            "env": {"REMOTE_ADDR": "203.0.113.7"},
        },
        "user": {"id": "u1", "ip_address": "203.0.113.7", "email": "x@example.com"},
    }
    out = scrub_event(event, {})
    assert out["request"] == {}
    assert out["user"] == {"id": "u1"}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("mode=roast&code=abc&state=xyz", f"mode=roast&code={_FILTERED}&state={_FILTERED}"),
        ("auth=failed&sort=new&page=2", "auth=failed&sort=new&page=2"),
        ("access_token=t&x=1", f"access_token={_FILTERED}&x=1"),
    ],
)
def test_sensitive_query_values_are_filtered(query, expected):
    event = {"request": {"query_string": query, "url": f"https://api.test/auth/callback?{query}"}}
    out = scrub_event(event, {})["request"]
    assert out["query_string"] == expected
    assert out["url"] == f"https://api.test/auth/callback?{expected}"


def test_query_strings_in_other_shapes_are_filtered():
    as_dict = scrub_event({"request": {"query_string": {"code": "a", "mode": "roast"}}}, {})
    as_pairs = scrub_event({"request": {"query_string": [["state", "a"], ["page", "2"]]}}, {})
    assert as_dict["request"]["query_string"] == {"code": _FILTERED, "mode": "roast"}
    assert as_pairs["request"]["query_string"] == [["state", _FILTERED], ["page", "2"]]


def test_url_edge_cases_are_left_intact():
    cases = {
        "https://api.test/x?code=a#frag": f"https://api.test/x?code={_FILTERED}#frag",
        "https://api.test/x?code&mode=roast": "https://api.test/x?code&mode=roast",
        "https://api.test/x?": "https://api.test/x?",
        "https://api.test/x": "https://api.test/x",
        "/me?state=s": f"/me?state={_FILTERED}",
    }
    for url, expected in cases.items():
        assert scrub_event({"request": {"url": url}}, {})["request"]["url"] == expected


def test_encoded_values_are_filtered_whole():
    out = scrub_event({"request": {"query_string": "code=a%2Fb%3D&mode=r%C3%B6ast"}}, {})
    assert out["request"]["query_string"] == f"code={_FILTERED}&mode=r%C3%B6ast"


def test_transaction_trace_and_span_data_keep_only_safe_values():
    data = {
        "http.request.header.user_agent": "pytest",
        "http.request.header.referer": "https://skillissue.tech/me?state=s",
        "http.request.header.x_internal_secret": _FILTERED,
        "http.request.header.cookie.si_session": "s",
        "http.response.header.set_cookie": "s",
        "http.request.body.data": "{}",
        "http.target": "/auth/callback?code=abc&mode=roast",
        "http.query": "state=xyz",
        "url.full": "https://api.test/x?token=t",
        "http.request.method": "GET",
    }
    event = {
        "type": "transaction",
        "contexts": {"trace": {"data": dict(data)}},
        "spans": [{"data": dict(data)}],
    }
    out = scrub_event(event, {})
    expected = {
        "http.request.header.user_agent": "pytest",
        "http.request.header.referer": f"https://skillissue.tech/me?state={_FILTERED}",
        "http.target": f"/auth/callback?code={_FILTERED}&mode=roast",
        "http.query": f"state={_FILTERED}",
        "url.full": f"https://api.test/x?token={_FILTERED}",
        "http.request.method": "GET",
    }
    assert out["contexts"]["trace"]["data"] == expected
    assert out["spans"][0]["data"] == expected


def test_breadcrumb_urls_are_filtered():
    event = {
        "breadcrumbs": {
            "values": [
                {
                    "category": "httplib",
                    "data": {"url": "https://api.test/x?token=t", "http.query": "code=c"},
                },
                {"category": "navigation", "data": {"from": "/a?state=s", "to": "/b"}},
            ]
        }
    }
    values = scrub_event(event, {})["breadcrumbs"]["values"]
    assert values[0]["data"] == {
        "url": f"https://api.test/x?token={_FILTERED}",
        "http.query": f"code={_FILTERED}",
    }
    assert values[1]["data"] == {"from": f"/a?state={_FILTERED}", "to": "/b"}


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        ({"request": None}, {}),
        ({"request": "x"}, {}),
        ({"request": {"headers": [("cookie", "s")]}}, {"request": {}}),
        ({"request": {"query_string": 3}}, {"request": {}}),
        ({"request": {"url": 7}}, {"request": {}}),
        ({"user": "x"}, {}),
        ({"contexts": 1}, {}),
        ({"contexts": {"trace": {"data": "x"}}}, {"contexts": {"trace": {}}}),
        ({"spans": "x"}, {}),
        ({"spans": [{"data": 1}]}, {"spans": [{}]}),
        ({"breadcrumbs": 5}, {}),
        ({"breadcrumbs": {"values": [{"data": None}]}}, {"breadcrumbs": {"values": [{}]}}),
    ],
)
def test_unreadable_parts_are_dropped_not_sent(event, expected):
    assert scrub_event(copy.deepcopy(event), {}) == expected


def test_one_bad_part_does_not_cost_the_rest():
    event = {
        "request": {"headers": "not-a-dict", "url": "https://api.test/x?code=c"},
        "contexts": {"auth": {"access_token": "t", "kept": "yes"}},
        "message": "boom",
    }
    out = scrub_event(event, {})
    assert out == {
        "request": {"url": f"https://api.test/x?code={_FILTERED}"},
        "contexts": {"auth": {"kept": "yes"}},
        "message": "boom",
    }


def test_an_event_without_request_details_is_unchanged():
    event = {
        "message": "hi",
        "level": "error",
        "tags": {"request_id": "r"},
        "request": {"method": "GET"},
    }
    assert scrub_event(copy.deepcopy(event), {}) == event
