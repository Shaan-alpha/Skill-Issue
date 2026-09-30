"""Writes must be committed before the response leaves the server.

FastAPI runs the teardown of a `yield` dependency *after* the response is sent
unless the dependency is declared with scope="function". `get_db` commits in
its teardown, so a request-scoped session lets the client act on a 2xx before
the write is visible: a fresh sign-in reads /me before its session row exists,
and a deleted analysis can reappear on the very next refresh.
"""

from __future__ import annotations

from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app

# The narrative route streams: it keeps writing after the handler returns, so
# it holds a request-scoped session and commits explicitly inside the stream.
STREAMING_ROUTES = {"/narrative/{username}"}


def _api_routes(routes):
    """Every APIRoute, including those inside included routers: FastAPI 0.141+
    keeps an included router behind a wrapper instead of copying its routes
    into `app.routes`."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "original_router"):
            yield from _api_routes(route.original_router.routes)


def _db_scopes(dependant) -> list[str | None]:
    scopes: list[str | None] = []
    for dep in dependant.dependencies:
        if dep.call is get_db:
            scopes.append(dep.scope)
        scopes.extend(_db_scopes(dep))
    return scopes


def test_every_non_streaming_route_commits_before_responding() -> None:
    offenders = {}
    for route in _api_routes(app.routes):
        if route.path in STREAMING_ROUTES:
            continue
        scopes = _db_scopes(route.dependant)
        if any(scope != "function" for scope in scopes):
            offenders[route.path] = scopes
    assert offenders == {}


def test_the_streaming_route_keeps_its_own_session_open() -> None:
    route = next(r for r in _api_routes(app.routes) if r.path == "/narrative/{username}")
    own = [d.scope for d in route.dependant.dependencies if d.call is get_db]
    assert own and own[0] != "function"


async def test_logout_commits_before_the_response_starts() -> None:
    events: list[str] = []

    class RecordingSession:
        async def execute(self, *_args, **_kwargs):
            events.append("execute")

        async def commit(self) -> None:
            events.append("commit")

        async def rollback(self) -> None:
            events.append("rollback")

    async def recording_get_db():
        session = RecordingSession()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def recording_app(scope, receive, send):
        async def send_and_record(message):
            if message["type"] == "http.response.start":
                events.append("response.start")
            await send(message)

        await app(scope, receive, send_and_record)

    app.dependency_overrides[get_db] = recording_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=recording_app), base_url="http://test"
        ) as client:
            client.cookies.set("si_session", "a-session-id")
            response = await client.post("/auth/logout")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 204
    assert events.index("commit") < events.index("response.start")
