from __future__ import annotations

from starlette.requests import Request

from app import settings as settings_module
from app.ratelimit import client_ip, is_trusted_proxy


def make_request(
    headers: dict[str, str] | None = None, client_host: str | None = "9.9.9.9"
) -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    scope: dict = {"type": "http", "headers": raw}
    if client_host is not None:
        scope["client"] = (client_host, 12345)
    return Request(scope)


def test_client_ip_prefers_forwarded_when_trusted():
    req = make_request({"x-client-ip": "1.2.3.4", "x-real-ip": "5.6.7.8"})
    assert client_ip(req, trusted_proxy=True) == "1.2.3.4"


def test_client_ip_ignores_forwarded_when_not_trusted():
    req = make_request({"x-client-ip": "1.2.3.4", "x-real-ip": "5.6.7.8"})
    assert client_ip(req, trusted_proxy=False) == "5.6.7.8"


def test_client_ip_uses_first_xff_hop():
    req = make_request({"x-forwarded-for": "11.11.11.11, 22.22.22.22"})
    assert client_ip(req, trusted_proxy=False) == "11.11.11.11"


def test_client_ip_falls_back_to_connection_host():
    req = make_request({}, client_host="3.3.3.3")
    assert client_ip(req, trusted_proxy=False) == "3.3.3.3"


def test_client_ip_unknown_when_nothing_available():
    req = make_request({}, client_host=None)
    assert client_ip(req, trusted_proxy=False) == "unknown"


def test_is_trusted_proxy_matches_secret(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "internal_proxy_secret", "s3cr3t")
    req = make_request({"x-internal-secret": "s3cr3t"})
    assert is_trusted_proxy(req) is True


def test_is_trusted_proxy_rejects_wrong_secret(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "internal_proxy_secret", "s3cr3t")
    req = make_request({"x-internal-secret": "nope"})
    assert is_trusted_proxy(req) is False


def test_is_trusted_proxy_false_when_secret_unset(monkeypatch):
    monkeypatch.setattr(settings_module.settings, "internal_proxy_secret", None)
    req = make_request({"x-internal-secret": "anything"})
    assert is_trusted_proxy(req) is False
