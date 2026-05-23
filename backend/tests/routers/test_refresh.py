import base64
import secrets

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.sessions import create_session
from app.db.models import User
from app.persistence.analyses import upsert_analysis


async def _setup_signed_in(db, monkeypatch) -> str:
    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    )
    from app import settings as settings_module

    settings_module.settings = settings_module.Settings()

    u = User(github_id=1, github_login="alice", name="A", avatar_url=None)
    db.add(u)
    await db.flush()
    sid = await create_session(db, user_id=u.id, github_access_token="gh-tok")
    await db.commit()
    return sid


async def _client():
    from app.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_refresh_without_session_returns_401():
    async with await _client() as ac:
        r = await ac.post("/me/refresh/octocat")
    assert r.status_code == 401


async def test_refresh_unsaved_target_returns_404(db, monkeypatch):
    sid = await _setup_signed_in(db, monkeypatch)
    from app.db.session import get_db
    from app.main import app

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            r = await ac.post("/me/refresh/never-saved")
        assert r.status_code == 404
        assert r.json() == {"detail": "no_saved_analysis"}
    finally:
        app.dependency_overrides.clear()


async def test_refresh_rate_limit_hits_429_on_11th_call(db, monkeypatch):
    sid = await _setup_signed_in(db, monkeypatch)
    u = await db.scalar(select(User).where(User.github_login == "alice"))
    assert u is not None
    await upsert_analysis(db, user_id=u.id, target_login="octocat")
    await db.commit()

    from app.db.session import get_db
    from app.main import app

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    # Inject a FakeRedis-backed cache so get_cache() returns it.
    from app.cache.client import RedisCache
    from tests.conftest import FakeRedis

    fake = FakeRedis()
    cache = RedisCache(redis=fake)
    monkeypatch.setattr("app.dependencies.get_cache", lambda: cache)
    monkeypatch.setattr("app.routers.refresh.get_cache", lambda: cache, raising=False)

    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            # First 10 calls — won't get past Task-6-stub (501) but we only
            # care about the rate-limit decision here, which is checked
            # BEFORE Task 6's pipeline.
            for i in range(10):
                r = await ac.post("/me/refresh/octocat")
                assert r.status_code != 429, f"call {i + 1} unexpectedly rate-limited"
            r11 = await ac.post("/me/refresh/octocat")
        assert r11.status_code == 429
        body = r11.json()
        assert body["detail"] == "rate_limited"
        assert body["retry_after_seconds"] > 0
        assert "retry-after" in {h.lower() for h in r11.headers}
    finally:
        app.dependency_overrides.clear()


def _stub_report():
    from datetime import UTC, datetime

    from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo

    return Report(
        username="octocat",
        total=42,
        generated_at=datetime.now(UTC),
        breakdown=ScoreBreakdown(
            repo_quality=ScoreResult(points=10, max_points=30, evidence=[]),
            engineering_maturity=ScoreResult(points=8, max_points=20, evidence=[]),
            oss_collab=ScoreResult(points=5, max_points=15, evidence=[]),
            consistency=ScoreResult(points=5, max_points=10, evidence=[]),
            recruiter_signal=ScoreResult(points=10, max_points=15, evidence=[]),
            learning_trajectory=ScoreResult(points=4, max_points=10, evidence=[]),
        ),
        tier=TierInfo(
            name="Hobbyist",
            sub_rank=42,
            band=(0, 50),
            next_tier="Student Builder",
            pts_to_next=8,
            prev_tier=None,
            pts_above_prev=42,
        ),
        badges=[],
    )


async def test_refresh_happy_path_returns_report_and_writes_run(db, monkeypatch):
    """Signed-in + owned target + mocked get_report_for_user + record_run →
    returns a Report-shaped body and writes a new analysis_runs row."""
    sid = await _setup_signed_in(db, monkeypatch)
    u = await db.scalar(select(User).where(User.github_login == "alice"))
    assert u is not None
    await upsert_analysis(db, user_id=u.id, target_login="octocat")
    await db.commit()

    from app.db.session import get_db
    from app.main import app

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    stub = _stub_report()

    async def _fake_get_report_for_user(username, session=None):
        return stub

    monkeypatch.setattr(
        "app.routers.refresh.get_report_for_user", _fake_get_report_for_user, raising=False
    )

    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            r = await ac.post("/me/refresh/octocat")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["username"] == "octocat"
        assert body["total"] == 42

        from app.db.models import AnalysisRun

        runs = (await db.execute(select(AnalysisRun))).scalars().all()
        assert any(run.total_score == 42 for run in runs), "expected fresh run row"
    finally:
        app.dependency_overrides.clear()


async def test_refresh_continues_when_cache_delete_fails(db, monkeypatch):
    """Layer A cache.delete is fail-open."""
    sid = await _setup_signed_in(db, monkeypatch)
    u = await db.scalar(select(User).where(User.github_login == "alice"))
    assert u is not None
    await upsert_analysis(db, user_id=u.id, target_login="octocat")
    await db.commit()

    from app.cache.client import RedisCache
    from app.db.session import get_db
    from app.main import app
    from tests.conftest import FakeRedis

    fake = FakeRedis()
    fake.fail_next = 1  # the next op (cache.delete) raises
    cache = RedisCache(redis=fake)
    monkeypatch.setattr("app.dependencies.get_cache", lambda: cache)
    monkeypatch.setattr("app.routers.refresh.get_cache", lambda: cache, raising=False)

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    stub = _stub_report()

    async def _fake_get_report_for_user(username, session=None):
        return stub

    monkeypatch.setattr(
        "app.routers.refresh.get_report_for_user", _fake_get_report_for_user, raising=False
    )

    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            r = await ac.post("/me/refresh/octocat")
        assert r.status_code == 200, r.text
    finally:
        app.dependency_overrides.clear()


async def test_refresh_saved_target_does_not_404_on_ownership(db, monkeypatch):
    """Signed-in user + saved target should NOT hit the 404 ownership branch.
    Will 501 here because Task 6 hasn't wired the live pipeline yet."""
    sid = await _setup_signed_in(db, monkeypatch)
    u = await db.scalar(select(User).where(User.github_login == "alice"))
    assert u is not None
    await upsert_analysis(db, user_id=u.id, target_login="octocat")
    await db.commit()

    from app.db.session import get_db
    from app.main import app

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    try:
        async with await _client() as ac:
            ac.cookies.set("si_session", sid)
            r = await ac.post("/me/refresh/octocat")
        # Anything except 404 with detail="no_saved_analysis" means we got past
        # the ownership check.
        assert not (r.status_code == 404 and r.json() == {"detail": "no_saved_analysis"})
    finally:
        app.dependency_overrides.clear()
