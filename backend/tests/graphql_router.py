"""Route mocked GitHub GraphQL POSTs by operation name.

A positional `side_effect=[...]` list hands each query whichever response is
next in line, so it silently depends on the order ingestion happens to issue
its queries. Routing by the operation name in the query text keeps a mock
correct however the calls are scheduled.
"""

import json
import re
from collections.abc import Callable, Mapping

from httpx import Request, Response

_OPERATION = re.compile(r"\bquery\s+(\w+)")

Payload = dict[str, object] | Response

# Operations asked for with no answer. Raising alone isn't enough: fail-soft
# code under test can swallow the error, so conftest also fails the test on
# anything recorded here.
_unrouted: list[str] = []


def take_unrouted() -> list[str]:
    """The operations no router could answer since the last call."""
    names = list(_unrouted)
    _unrouted.clear()
    return names


def graphql_router(
    responses: Mapping[str, Payload | list[Payload]],
) -> Callable[[Request], Response]:
    """Build a respx side effect answering each GraphQL operation by name.

    A value is a JSON payload, an `httpx.Response`, or a list of either served
    in order on repeated calls (the last one repeats once the list runs out).
    An operation with no entry fails the test, even if the code under test
    swallows the error.
    """
    served: dict[str, int] = {}

    def _route(request: Request) -> Response:
        query = json.loads(request.content)["query"]
        match = _OPERATION.search(query)
        name = match.group(1) if match else "<anonymous>"
        if name not in responses:
            _unrouted.append(name)
            raise AssertionError(f"unexpected GraphQL operation {name!r}")
        value = responses[name]
        if isinstance(value, list):
            index = min(served.get(name, 0), len(value) - 1)
            served[name] = served.get(name, 0) + 1
            value = value[index]
        return value if isinstance(value, Response) else Response(200, json=value)

    return _route
