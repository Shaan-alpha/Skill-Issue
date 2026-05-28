from __future__ import annotations

from unittest.mock import patch

import app.settings as settings_module
from app.db.engine import _build_engine
from app.settings import Settings

_URL = "postgresql+asyncpg://u:p@localhost:5432/db"


def test_engine_pool_uses_settings_defaults():
    """With no env override, the builder passes the 5/5 defaults through."""
    with patch("app.db.engine.create_async_engine") as mock_create:
        _build_engine(_URL)
    kwargs = mock_create.call_args.kwargs
    assert kwargs["pool_size"] == 5
    assert kwargs["max_overflow"] == 5


def test_engine_pool_reads_env_override(monkeypatch):
    """Monkeypatching the live settings object flows into the built engine —
    proves _build_engine reads via the module reference, not an import-time bind."""
    monkeypatch.setattr(
        settings_module,
        "settings",
        Settings(db_pool_size=10, db_max_overflow=20),
    )
    with patch("app.db.engine.create_async_engine") as mock_create:
        _build_engine(_URL)
    kwargs = mock_create.call_args.kwargs
    assert kwargs["pool_size"] == 10
    assert kwargs["max_overflow"] == 20
