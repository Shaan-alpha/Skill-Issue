from __future__ import annotations

import gzip
import json
import zlib

import pytest

from tools.sentry_envelope_listener import decode_body, find_canaries, item_types

_ENVELOPE = b"\n".join(
    [
        json.dumps({"event_id": "e1", "dsn": "http://public@127.0.0.1:9999/1"}).encode(),
        json.dumps({"type": "event", "length": 2}).encode(),
        b"{}",
        json.dumps({"type": "transaction"}).encode(),
        json.dumps({"type": "transaction", "request": {"headers": {"x": "canary-1"}}}).encode(),
    ]
)


def test_bodies_are_decoded_as_sent() -> None:
    assert decode_body(gzip.compress(_ENVELOPE), "gzip") == _ENVELOPE
    assert decode_body(zlib.compress(_ENVELOPE), "deflate") == _ENVELOPE
    assert decode_body(_ENVELOPE, None) == _ENVELOPE


def test_an_unknown_encoding_fails_loudly() -> None:
    with pytest.raises(ValueError, match="br"):
        decode_body(b"x", "br")


def test_canaries_are_found_anywhere_in_an_envelope() -> None:
    assert find_canaries(_ENVELOPE, ["canary-1", "canary-2"]) == ["canary-1"]


def test_item_types_come_from_item_headers_only() -> None:
    assert item_types(_ENVELOPE) == ["event", "transaction"]
