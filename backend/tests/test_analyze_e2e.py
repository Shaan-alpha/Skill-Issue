"""End-to-end test for GET /analyze/{username}.

Exercises the real ingestion → scoring → response serialization path with
GitHub HTTP responses mocked at the network layer. Locks the contract the
unit tests can't see: that the data shapes ingestion produces are exactly
what the scorers expect.
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from app import dependencies as dep_module
from app import main as app_module
from app.settings import Settings
from tests.graphql_router import graphql_router


@pytest.fixture
def _settings_with_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the app to see a github_token without touching the real .env."""
    monkeypatch.setattr(app_module, "settings", Settings(github_token="ghs_test"))
    monkeypatch.setattr(dep_module, "settings", Settings(github_token="ghs_test"))


def _user_payload(login: str = "testuser") -> dict[str, Any]:
    return {
        "login": login,
        "id": 1,
        "bio": "Builds things.",
        "followers": 42,
        "public_repos": 3,
        "created_at": "2020-01-15T00:00:00Z",
        "company": "@example-co",
        "blog": "https://example.dev",
        "hireable": True,
    }


def _repo_payload(name: str, *, language: str, days_since_push: int = 5) -> dict[str, Any]:
    pushed = (datetime.now(UTC) - timedelta(days=days_since_push)).isoformat()
    return {
        "name": name,
        "full_name": f"testuser/{name}",
        "owner": {"login": "testuser"},
        "language": language,
        "stargazers_count": 75,
        "forks_count": 3,
        "fork": False,
        "size": 512,
        "pushed_at": pushed,
        "created_at": "2021-06-01T00:00:00Z",
        "license": {"key": "mit", "spdx_id": "MIT"},
    }


def _commit_payload(days_ago: int) -> dict[str, Any]:
    when = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    return {"commit": {"author": {"date": when}}}


def _activity_from(commits_by_repo: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """The CommitActivity answer for the same commits, split into the last
    year and the year before: commit days now come from contribution data."""
    year_ago = datetime.now(UTC) - timedelta(days=365)

    def repo(days: set[str]) -> dict[str, Any]:
        return {
            "repository": {"isPrivate": False},
            "contributions": {
                "totalCount": len(days),
                "pageInfo": {"hasNextPage": False},
                "nodes": [{"occurredAt": f"{d}T07:00:00Z"} for d in sorted(days, reverse=True)],
            },
        }

    last_year: list[dict[str, Any]] = []
    prior_year: list[dict[str, Any]] = []
    for commits in commits_by_repo.values():
        days = {str(c["commit"]["author"]["date"])[:10] for c in commits}
        recent = {d for d in days if datetime.fromisoformat(d).replace(tzinfo=UTC) > year_ago}
        if recent:
            last_year.append(repo(recent))
        if days - recent:
            prior_year.append(repo(days - recent))
    return {
        "data": {
            "user": {
                "lastYear": {"commitContributionsByRepository": last_year},
                "priorYear": {"commitContributionsByRepository": prior_year},
            }
        }
    }


def _mock_github_for_testuser(
    repos: list[dict[str, Any]],
    commits_by_repo: dict[str, list[dict[str, Any]]],
    graphql_overrides: dict[str, Any] | None = None,
) -> None:
    respx.get("https://api.github.com/users/testuser").mock(
        return_value=Response(200, json=_user_payload())
    )
    respx.get("https://api.github.com/users/testuser/repos").mock(
        return_value=Response(200, json=repos)
    )
    encoded = base64.b64encode(b"# Hello world").decode("ascii")
    respx.get("https://api.github.com/repos/testuser/testuser/readme").mock(
        return_value=Response(200, json={"content": encoded, "encoding": "base64"})
    )
    for repo in repos:
        owner, name = str(repo["full_name"]).split("/", 1)
        respx.get(f"https://api.github.com/repos/{owner}/{name}/languages").mock(
            return_value=Response(200, json={repo["language"]: 1000})
        )
        respx.get(url__startswith=f"https://api.github.com/repos/{owner}/{name}/commits").mock(
            return_value=Response(200, json=commits_by_repo.get(name, []))
        )
        # Root-contents enrichment: give every test repo a healthy set of signals
        # so the e2e contract test exercises the README/tests/CI/deployment paths.
        respx.get(f"https://api.github.com/repos/{owner}/{name}/contents").mock(
            return_value=Response(
                200,
                json=[
                    {"name": "README.md", "type": "file"},
                    {"name": "tests", "type": "dir"},
                    {"name": ".github", "type": "dir"},
                    {"name": "Dockerfile", "type": "file"},
                ],
            )
        )
        respx.get(f"https://api.github.com/repos/{owner}/{name}/readme").mock(
            return_value=Response(
                200,
                json={
                    "content": base64.b64encode(b"# README\n## Setup").decode(),
                    "encoding": "base64",
                },
            )
        )

    respx.post("https://api.github.com/graphql").mock(
        side_effect=graphql_router(
            {
                "PinnedRepos": {"data": {"user": {"pinnedItems": {"totalCount": 0}}}},
                "ExternalPRs": {
                    "data": {
                        "user": {
                            "hasSponsorsListing": False,
                            "isGitHubStar": False,
                            "isDeveloperProgramMember": False,
                        },
                        "search": {"issueCount": 0, "nodes": []},
                    }
                },
                "ExternalReviewCount": {
                    "data": {
                        "user": {
                            "contributionsCollection": {
                                "pullRequestReviewContributions": {"totalCount": 0}
                            }
                        }
                    }
                },
                "ReviewDepth": {
                    "data": {
                        "user": {
                            "contributionsCollection": {
                                "pullRequestReviewContributions": {"nodes": []}
                            }
                        }
                    }
                },
                "WorkflowFiles": {
                    "data": {
                        f"r{i}": {"github": {"entries": [{"name": "ci.yml", "type": "blob"}]}}
                        for i in range(3)
                    }
                },
                "CommitActivity": _activity_from(commits_by_repo),
                **(graphql_overrides or {}),
            }
        )
    )


@pytest.mark.asyncio
@respx.mock
async def test_analyze_returns_complete_report(
    _settings_with_token: None,
) -> None:
    """Happy path: every scorer runs, breakdown is complete, total = sum of
    parts."""
    repos = [
        _repo_payload("alpha", language="TypeScript"),
        _repo_payload("beta", language="Python"),
    ]
    # 35 commit days spread across the last 90 days — exercises consistency
    # cadence + dry-spell + volume signals against tz-aware UTC datetimes.
    commits = [_commit_payload(days_ago=i * 2) for i in range(35)]
    _mock_github_for_testuser(repos, {"alpha": commits, "beta": commits[:5]})

    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analyze/testuser")

    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Shape: every bucket the frontend reads must be present.
    assert body["username"] == "testuser"
    assert "tier" in body
    tier = body["tier"]
    assert tier["name"] in {
        "Hobbyist",
        "Student Builder",
        "Entry-Level Engineer",
        "Professional Developer",
        "Senior Engineer",
        "Staff Engineer",
        "Principal Engineer",
    }
    assert 0 <= tier["sub_rank"] <= 100
    assert isinstance(body["badges"], list)
    breakdown = body["breakdown"]
    expected_keys = {
        "repo_quality",
        "engineering_maturity",
        "oss_collab",
        "consistency",
        "recruiter_signal",
        "learning_trajectory",
    }
    assert set(breakdown) == expected_keys

    for key, bucket in breakdown.items():
        assert isinstance(bucket["points"], int), key
        assert isinstance(bucket["max_points"], int), key
        assert 0 <= bucket["points"] <= bucket["max_points"], key
        assert isinstance(bucket["evidence"], list), key

    # The headline number must be the literal sum of the buckets. No fudge.
    assert body["total"] == sum(b["points"] for b in breakdown.values())
    assert 0 <= body["total"] <= 100

    # Commit days came from contribution data, not the fallback sample.
    volume = [
        e["detail"] for e in breakdown["consistency"]["evidence"] if e["signal"] == "high_volume"
    ]
    assert volume == ["Committed on 35 days in the last year across public repositories"]

    # Regression guard for the two bugs we shipped in v0.1.0:
    # - consistency.score crashed on strptime(datetime, ...)
    # - learning_trajectory.score crashed comparing naive vs aware datetimes
    # Reaching this assertion at all proves both paths ran without raising.
    assert breakdown["consistency"]["max_points"] == 10
    assert breakdown["learning_trajectory"]["max_points"] == 10


_RATE_LIMITED = Response(
    403,
    json={"message": "API rate limit exceeded for user ID 1."},
    headers={"Retry-After": "0", "X-RateLimit-Remaining": "0"},
)


def _senior_tier_testuser(graphql_overrides: dict[str, Any] | None = None) -> None:
    """Mocks for a profile whose base score clears Senior Engineer, so the
    tier-gated depth enrichment queries GitHub after ingestion."""
    repos = [
        _repo_payload("alpha", language="TypeScript"),
        _repo_payload("beta", language="Python"),
    ]
    commits = [_commit_payload(days_ago=i * 2) for i in range(35)]
    last_year = [*commits[:5], _commit_payload(days_ago=400)]
    _mock_github_for_testuser(repos, {"alpha": commits, "beta": last_year}, graphql_overrides)


async def _get_analyze(path: str = "/analyze/testuser") -> Any:
    # A crash must come back as the 500 a real client sees, not raise here.
    transport = ASGITransport(app=app_module.app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


@pytest.mark.asyncio
@respx.mock
async def test_rate_limited_ingest_is_service_busy(_settings_with_token: None) -> None:
    _senior_tier_testuser()
    respx.get("https://api.github.com/repos/testuser/alpha/contents").mock(
        return_value=_RATE_LIMITED
    )

    resp = await _get_analyze()

    assert resp.status_code == 503
    assert resp.json() == {"error": "service_busy"}


@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_during_depth_enrichment_is_service_busy_not_a_crash(
    _settings_with_token: None,
) -> None:
    _senior_tier_testuser(graphql_overrides={"ReviewDepth": _RATE_LIMITED})

    resp = await _get_analyze()

    assert resp.status_code == 503
    assert resp.json() == {"error": "service_busy"}


@pytest.mark.asyncio
@respx.mock
async def test_call_cap_reached_during_depth_enrichment_is_a_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.github.client import GitHubClient
    from app.ingestion.profile import ingest_profile

    _senior_tier_testuser()
    # Measure what ingestion alone costs, then cap the analysis exactly there:
    # ingestion completes and the first depth-enrichment call exceeds the cap.
    async with GitHubClient(token="ghs_test") as gh:
        await ingest_profile("testuser", gh)
    ingest_calls = respx.calls.call_count
    capped = Settings(github_token="ghs_test", gh_max_calls_per_analysis=ingest_calls)
    monkeypatch.setattr(app_module, "settings", capped)
    monkeypatch.setattr(dep_module, "settings", capped)

    resp = await _get_analyze()

    assert resp.status_code == 503
    assert resp.json() == {"error": "analysis_too_large"}


@pytest.mark.asyncio
@respx.mock
async def test_whole_analysis_never_exceeds_the_concurrency_cap() -> None:
    """Depth enrichment used to fan out outside the ingestion semaphore, up to
    thirty requests at once. The cap lives in the client now, so ingestion and
    scoring together stay under it."""
    import asyncio

    from app.github.client import GitHubClient
    from app.ingestion.profile import ingest_profile
    from app.scoring.engine import run_scoring_engine

    _senior_tier_testuser()
    current = peak = 0
    queries: list[str] = []

    async with GitHubClient(token="ghs_test", max_concurrency=4) as gh:
        send = gh._client.request

        async def tracked(*args: Any, **kwargs: Any) -> Any:
            nonlocal current, peak
            queries.append((kwargs.get("json") or {}).get("query", ""))
            current += 1
            peak = max(peak, current)
            try:
                await asyncio.sleep(0.005)
                return await send(*args, **kwargs)
            finally:
                current -= 1

        gh._client.request = tracked  # type: ignore[method-assign]
        profile = await ingest_profile("testuser", gh)
        await run_scoring_engine(profile, gh)

    # Depth enrichment's own request was among those measured.
    assert any("query ReviewDepth(" in q for q in queries)
    assert 1 < peak <= 4


@pytest.mark.asyncio
@respx.mock
async def test_analyze_unknown_user_returns_404(
    _settings_with_token: None,
) -> None:
    respx.get("https://api.github.com/users/ghost").mock(
        return_value=Response(404, json={"message": "Not Found"})
    )

    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analyze/ghost")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_username",
    [
        "-leading-hyphen",
        "trailing-hyphen-",
        "double--hyphen",
        "has space",
        "has/slash",
        "name@with@at",
        "a" * 40,
        "",
    ],
)
async def test_analyze_rejects_invalid_username(
    _settings_with_token: None, bad_username: str
) -> None:
    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/analyze/{bad_username}")

    # FastAPI returns 404 when the path itself is empty; the validator handles
    # the rest with 400.
    assert resp.status_code in {400, 404}


@pytest.mark.asyncio
async def test_analyze_without_token_returns_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(app_module, "settings", Settings(github_token=None))
    monkeypatch.setattr(dep_module, "settings", Settings(github_token=None))
    transport = ASGITransport(app=app_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/analyze/anybody")

    assert resp.status_code == 500
    assert "GITHUB_TOKEN" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_signed_in_analyze_persists_run(db, monkeypatch):
    """When a session cookie is sent, /analyze writes an analyses + analysis_runs row."""
    import base64
    import secrets

    from httpx import ASGITransport, AsyncClient

    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    )
    monkeypatch.setenv("GITHUB_TOKEN", "project-token")

    from sqlalchemy import select

    from app.auth.sessions import create_session
    from app.db.models import Analysis, AnalysisRun, User
    from app.main import app

    u = User(github_id=1, github_login="me")
    db.add(u)
    await db.flush()
    sid = await create_session(db, user_id=u.id, github_access_token="user-token", ttl_days=30)
    await db.commit()

    from app import dependencies as deps

    async def fake_ingest(username, gh):
        return type("P", (), {"login": username})()

    async def fake_run_engine(profile, gh):
        from datetime import UTC, datetime

        from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo

        return Report(
            username=profile.login,
            tier=TierInfo(
                name="Senior Engineer",
                sub_rank=50,
                band=[65, 80],
                next_tier="Staff Engineer",
                chip_label="50% into tier",
            ),
            badges=[],
            breakdown=ScoreBreakdown(
                repo_quality=ScoreResult(points=20, max_points=30),
                engineering_maturity=ScoreResult(points=10, max_points=20),
                oss_collab=ScoreResult(points=10, max_points=15),
                consistency=ScoreResult(points=5, max_points=10),
                recruiter_signal=ScoreResult(points=10, max_points=15),
                learning_trajectory=ScoreResult(points=5, max_points=10),
            ),
            total=60,
            generated_at=datetime.now(UTC),
        )

    monkeypatch.setattr(deps, "ingest_profile", fake_ingest)
    monkeypatch.setattr(deps, "run_scoring_engine", fake_run_engine)

    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        ac.cookies.set("si_session", sid)
        r = await ac.get("/analyze/octocat")
    app.dependency_overrides.clear()
    assert r.status_code == 200

    analysis = await db.scalar(
        select(Analysis).where(Analysis.user_id == u.id, Analysis.target_login == "octocat")
    )
    assert analysis is not None
    run = await db.scalar(select(AnalysisRun).where(AnalysisRun.analysis_id == analysis.id))
    assert run is not None
    assert run.total_score == 60
    assert run.tier_name == "Senior Engineer"
    assert analysis.latest_run_id == run.id


@pytest.mark.asyncio
async def test_anonymous_analyze_does_not_persist(db, monkeypatch):
    """Anonymous /analyze writes nothing — landing-page demo flow unchanged."""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import func, select

    from app import dependencies as deps
    from app.db.models import Analysis
    from app.main import app

    monkeypatch.setenv("GITHUB_TOKEN", "project-token")
    # setenv alone does nothing here: app/dependencies.py binds the settings
    # object at import via `from app.settings import settings`, so it keeps
    # whatever GITHUB_TOKEN was on disk. This is the anonymous path, which has
    # no session token to fall back on, so with an unset token the request 500s
    # at the "GITHUB_TOKEN not configured" guard. It passed only on machines
    # with a real token in .env, and failed the moment it ran in CI.
    monkeypatch.setattr(deps.settings, "github_token", "project-token")

    async def fake_ingest(username, gh):
        return type("P", (), {"login": username})()

    async def fake_run_engine(profile, gh):
        from datetime import UTC, datetime

        from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo

        return Report(
            username=profile.login,
            tier=TierInfo(
                name="Hobbyist",
                sub_rank=10,
                band=[0, 30],
                next_tier="Student Builder",
                chip_label="10% into tier",
            ),
            badges=[],
            breakdown=ScoreBreakdown(
                repo_quality=ScoreResult(points=0, max_points=30),
                engineering_maturity=ScoreResult(points=0, max_points=20),
                oss_collab=ScoreResult(points=0, max_points=15),
                consistency=ScoreResult(points=0, max_points=10),
                recruiter_signal=ScoreResult(points=0, max_points=15),
                learning_trajectory=ScoreResult(points=0, max_points=10),
            ),
            total=0,
            generated_at=datetime.now(UTC),
        )

    monkeypatch.setattr(deps, "ingest_profile", fake_ingest)
    monkeypatch.setattr(deps, "run_scoring_engine", fake_run_engine)

    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.get("/analyze/octocat")
    app.dependency_overrides.clear()
    assert r.status_code == 200
    count = await db.scalar(select(func.count()).select_from(Analysis))
    assert count == 0


def _fixed_report(generated_at: datetime) -> Any:
    from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo

    return Report(
        username="octocat",
        tier=TierInfo(name="Senior Engineer", sub_rank=50, band=(65, 80)),
        badges=[],
        breakdown=ScoreBreakdown(
            repo_quality=ScoreResult(points=20, max_points=30),
            engineering_maturity=ScoreResult(points=10, max_points=20),
            oss_collab=ScoreResult(points=10, max_points=15),
            consistency=ScoreResult(points=5, max_points=10),
            recruiter_signal=ScoreResult(points=15, max_points=15),
            learning_trajectory=ScoreResult(points=10, max_points=10),
        ),
        total=70,
        generated_at=generated_at,
    )


async def _signed_in_analyze(db, monkeypatch, reports: list[Any], *, delay: float = 0.0) -> Any:
    """GET /analyze/octocat once per report as a signed-in user; return the user."""
    import asyncio
    import base64
    import secrets

    from app.auth.sessions import create_session
    from app.db.models import User
    from app.db.session import get_db

    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    )
    user = User(github_id=5, github_login="me")
    db.add(user)
    await db.flush()
    sid = await create_session(db, user_id=user.id, github_access_token="t", ttl_days=30)
    await db.commit()

    queue = list(reports)

    async def _report() -> Any:
        await asyncio.sleep(delay)
        return queue.pop(0)

    async def _db() -> Any:
        yield db

    app_module.app.dependency_overrides[dep_module.get_report_for_user] = _report
    app_module.app.dependency_overrides[get_db] = _db
    try:
        transport = ASGITransport(app=app_module.app)
        async with AsyncClient(transport=transport, base_url="http://t") as client:
            client.cookies.set("si_session", sid)
            for _ in reports:
                assert (await client.get("/analyze/octocat")).status_code == 200
    finally:
        app_module.app.dependency_overrides.clear()
    return user


async def _runs(db) -> list[Any]:
    from sqlalchemy import select

    from app.db.models import AnalysisRun

    db.expunge_all()
    return list((await db.scalars(select(AnalysisRun))).all())


@pytest.mark.asyncio
async def test_viewing_the_same_report_again_records_no_new_run(db, monkeypatch) -> None:
    """A cached report re-served on every page view is the same run. Each view
    used to store another copy of the full report JSON."""
    report = _fixed_report(datetime(2026, 10, 1, tzinfo=UTC))
    await _signed_in_analyze(db, monkeypatch, [report, report, report])

    assert len(await _runs(db)) == 1


@pytest.mark.asyncio
async def test_a_newly_scored_report_records_a_new_run(db, monkeypatch) -> None:
    await _signed_in_analyze(
        db,
        monkeypatch,
        [
            _fixed_report(datetime(2026, 10, 1, tzinfo=UTC)),
            _fixed_report(datetime(2026, 10, 2, tzinfo=UTC)),
        ],
    )

    assert len(await _runs(db)) == 2


@pytest.mark.asyncio
async def test_recorded_latency_covers_producing_the_report(db, monkeypatch) -> None:
    """The clock started after the report dependency had already run, so every
    recorded latency was about 0ms."""
    await _signed_in_analyze(
        db, monkeypatch, [_fixed_report(datetime(2026, 10, 1, tzinfo=UTC))], delay=0.15
    )

    (run,) = await _runs(db)
    assert run.ingestion_latency_ms >= 150
