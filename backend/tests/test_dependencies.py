"""Verifies `get_report_for_user` consults the optional session for the GitHub token."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.dependencies import get_report_for_user


@pytest.mark.asyncio
async def test_uses_session_token_when_session_present(monkeypatch):
    sentinel_report = MagicMock(username="x", total=42)
    captured: dict[str, str] = {}

    class FakeClient:
        def __init__(self, token: str, *, cache=None, max_retries: int = 3, max_calls=None):
            captured["token"] = token

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    async def fake_ingest(username, gh):
        return MagicMock(login=username)

    async def fake_run_scoring_engine(profile, gh):
        return sentinel_report

    monkeypatch.setattr("app.dependencies.GitHubClient", FakeClient)
    monkeypatch.setattr("app.dependencies.ingest_profile", fake_ingest)
    monkeypatch.setattr("app.dependencies.run_scoring_engine", fake_run_scoring_engine)

    class FakeSession:
        access_token = "user-token-abc"

    out = await get_report_for_user("octocat", session=FakeSession())
    assert out is sentinel_report
    assert captured["token"] == "user-token-abc"


@pytest.mark.asyncio
async def test_falls_back_to_project_token_when_no_session(monkeypatch):
    captured: dict[str, str] = {}

    class FakeClient:
        def __init__(self, token: str, *, cache=None, max_retries: int = 3, max_calls=None):
            captured["token"] = token

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return None

    monkeypatch.setenv("GITHUB_TOKEN", "project-token")
    # Reload settings so it sees the env var.
    from importlib import reload

    import app.dependencies as deps_mod
    from app import settings as settings_mod

    reload(settings_mod)
    reload(deps_mod)

    monkeypatch.setattr(deps_mod, "GitHubClient", FakeClient)
    monkeypatch.setattr(deps_mod, "ingest_profile", AsyncMock(return_value=MagicMock()))
    monkeypatch.setattr(deps_mod, "run_scoring_engine", AsyncMock(return_value=MagicMock()))

    await deps_mod.get_report_for_user("octocat", session=None)
    assert captured["token"] == "project-token"


async def test_call_cap_exceeded_maps_to_503(monkeypatch):
    from fastapi import HTTPException

    import app.dependencies as deps
    from app.github.client import GitHubCallCapExceeded

    async def _boom(username, gh):
        raise GitHubCallCapExceeded(151, 150)

    monkeypatch.setattr(deps, "ingest_profile", _boom)
    monkeypatch.setattr(deps.settings, "github_token", "t", raising=False)
    with pytest.raises(HTTPException) as exc:
        await deps._live_ingest("octocat", None, cache=None)
    assert exc.value.status_code == 503
    assert exc.value.detail["error"] == "analysis_too_large"
