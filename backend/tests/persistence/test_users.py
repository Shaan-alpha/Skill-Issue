from sqlalchemy import select

from app.db.models import User
from app.persistence.users import upsert_user_from_github_payload


async def test_insert_new_user(db):
    payload = {"id": 1, "login": "alice", "name": "Alice", "avatar_url": "u"}
    user = await upsert_user_from_github_payload(db, payload)
    assert user.github_id == 1
    assert user.github_login == "alice"
    assert user.name == "Alice"
    assert user.avatar_url == "u"
    assert user.id is not None  # primary key allocated


async def test_upsert_existing_user_updates_mutable_fields(db):
    db.add(User(github_id=1, github_login="alice", name="Old"))
    await db.flush()
    payload = {"id": 1, "login": "alice2", "name": "Alice New", "avatar_url": "new"}
    user = await upsert_user_from_github_payload(db, payload)
    assert user.github_login == "alice2"
    assert user.name == "Alice New"
    assert user.avatar_url == "new"
    # No duplicate row
    rows = (await db.scalars(select(User).where(User.github_id == 1))).all()
    assert len(rows) == 1


async def test_upsert_tolerates_missing_optional_fields(db):
    payload = {"id": 5, "login": "x"}  # no name, no avatar_url
    user = await upsert_user_from_github_payload(db, payload)
    assert user.name is None
    assert user.avatar_url is None
