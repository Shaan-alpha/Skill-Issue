from datetime import UTC, datetime

from app.db.models import User
from app.persistence.analyses import record_run, upsert_analysis
from app.persistence.narratives import save_narrative


async def _seed_run(db) -> int:
    u = User(github_id=1, github_login="x")
    db.add(u)
    await db.flush()
    a = await upsert_analysis(db, user_id=u.id, target_login="t")
    r = await record_run(db, analysis_id=a.id, report_json={}, total_score=50,
                         tier_name="X", scores_hash="h",
                         started_at=datetime.now(UTC), completed_at=datetime.now(UTC),
                         latency_ms=1)
    return r.id


async def test_save_inserts_new_narrative(db):
    rid = await _seed_run(db)
    n = await save_narrative(
        db, analysis_run_id=rid, mode="roast", text="hi",
        provider="openai", model_name="gpt-4o", is_fallback=False,
    )
    assert n.mode == "roast"
    assert n.text == "hi"
    assert n.provider == "openai"


async def test_save_upserts_on_same_run_mode(db):
    rid = await _seed_run(db)
    n1 = await save_narrative(db, analysis_run_id=rid, mode="roast", text="old",
                              provider="openai", model_name="m", is_fallback=False)
    n2 = await save_narrative(db, analysis_run_id=rid, mode="roast", text="new",
                              provider="openai", model_name="m", is_fallback=False)
    assert n1.id == n2.id
    assert n2.text == "new"


async def test_fallback_narrative_has_no_model_name(db):
    rid = await _seed_run(db)
    n = await save_narrative(db, analysis_run_id=rid, mode="mentor", text="ok",
                             provider="fallback", model_name=None, is_fallback=True)
    assert n.provider == "fallback"
    assert n.model_name is None
    assert n.is_fallback is True
