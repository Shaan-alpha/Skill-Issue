"""Stop the clock inside one module under test."""

from datetime import datetime, tzinfo


def frozen_at(moment: datetime) -> type[datetime]:
    """A `datetime` whose now() is always `moment`. Patch it over the module's
    `datetime` name: `monkeypatch.setattr(module, "datetime", frozen_at(...))`."""

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> datetime:
            return moment if tz is None else moment.astimezone(tz)

    return _Frozen
