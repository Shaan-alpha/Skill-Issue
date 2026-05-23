from app.cache.keys import NAMESPACE_RATE_LIMIT, rate_limit_key


def test_namespace_value():
    assert NAMESPACE_RATE_LIMIT == "rate_limit"


def test_key_shape_includes_name_user_id_hour_bucket():
    k = rate_limit_key("force_refresh", user_id=42, hour_bucket="2026-05-22-14")
    assert k == "force_refresh:42:2026-05-22-14"


def test_key_isolates_different_names():
    a = rate_limit_key("force_refresh", user_id=1, hour_bucket="h")
    b = rate_limit_key("analyze", user_id=1, hour_bucket="h")
    assert a != b


def test_key_isolates_different_users():
    a = rate_limit_key("force_refresh", user_id=1, hour_bucket="h")
    b = rate_limit_key("force_refresh", user_id=2, hour_bucket="h")
    assert a != b
