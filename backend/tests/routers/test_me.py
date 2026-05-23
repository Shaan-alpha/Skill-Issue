import base64
import secrets
from datetime import UTC, datetime

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.sessions import create_session
from app.db.models import User
from app.main import app
from app.persistence.analyses import record_run, upsert_analysis


async def _setup_signed_in(db, monkeypatch) -> str:
    monkeypatch.setenv(
        "SESSION_TOKEN_ENC_KEY", base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    )
    u = User(github_id=1, github_login="alice", name="A", avatar_url=None)
    db.add(u)
    await db.flush()
    sid = await create_session(db, user_id=u.id, github_access_token="t", ttl_days=30)
    await db.commit()
    return sid


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_me_returns_user_and_count(db, monkeypatch):
    sid = await _setup_signed_in(db, monkeypatch)
    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    async with await _client() as ac:
        ac.cookies.set("si_session", sid)
        r = await ac.get("/me")
    app.dependency_overrides.clear()

    assert r.status_code == 200
    body = r.json()
    assert body["user"]["login"] == "alice"
    assert body["counts"]["analyses"] == 0


async def test_me_returns_401_without_session():
    async with await _client() as ac:
        r = await ac.get("/me")
    assert r.status_code == 401


async def test_me_analyses_paginated(db, monkeypatch):
    sid = await _setup_signed_in(db, monkeypatch)
    user = await db.scalar(select(User).where(User.github_login == "alice"))
    for i, target in enumerate(("a", "b", "c")):
        a = await upsert_analysis(db, user_id=user.id, target_login=target)
        await record_run(
            db,
            analysis_id=a.id,
            report_json={},
            total_score=10 * i,
            tier_name="X",
            scores_hash="h",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            latency_ms=1,
        )
    await db.commit()

    from app.db.session import get_db

    async def _o():
        yield db

    app.dependency_overrides[get_db] = _o

    async with await _client() as ac:
        ac.cookies.set("si_session", sid)
        r = await ac.get("/me/analyses?sort=score_desc&page=1")
    app.dependency_overrides.clear()
    body = r.json()
    assert body["total"] == 3
    assert body["analyses"][0]["target_login"] == "c"
