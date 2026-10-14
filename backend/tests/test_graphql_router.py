"""The GraphQL router must fail a test that issues an operation it has no
answer for, even when the code under test swallows the router's error."""

import contextlib

from httpx import Request

from tests.graphql_router import graphql_router, take_unrouted


def _request(operation: str) -> Request:
    return Request(
        "POST",
        "https://api.github.com/graphql",
        json={"query": f"query {operation}($login: String!) {{ user(login: $login) {{ id }} }}"},
    )


def test_an_unrouted_operation_is_recorded_even_when_its_error_is_swallowed() -> None:
    route = graphql_router({"Known": {"data": {}}})

    # Fail-soft code under test catches the router's AssertionError.
    with contextlib.suppress(AssertionError):
        route(_request("Unknown"))
    route(_request("Known"))

    assert take_unrouted() == ["Unknown"]
    assert take_unrouted() == []
