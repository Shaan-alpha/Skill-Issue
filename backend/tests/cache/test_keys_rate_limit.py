from app.cache.keys import NAMESPACE_RATE_LIMIT, rate_limit_key


def test_namespace_value():
    assert NAMESPACE_RATE_LIMIT == "rate_limit"


def test_key_shape_includes_name_subject_hour_bucket():
    k = rate_limit_key("force_refresh", subject="user:42", hour_bucket="2026-05-22-14")
    assert k == "force_refresh:user:42:2026-05-22-14"


def test_key_isolates_different_names():
    a = rate_limit_key("force_refresh", subject="user:1", hour_bucket="h")
    b = rate_limit_key("analyze", subject="user:1", hour_bucket="h")
    assert a != b


def test_key_isolates_user_from_ip_subject():
    a = rate_limit_key("analyze", subject="user:1", hour_bucket="h")
    b = rate_limit_key("analyze", subject="ip:1.2.3.4", hour_bucket="h")
    assert a != b
