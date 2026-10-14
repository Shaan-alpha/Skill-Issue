"""A local stand-in for Sentry that records envelopes, and a canary check.

A privacy smoke for the PII contract (docs/OBSERVABILITY.md): point an app's
DSN at this listener, send requests carrying canary values, then check that
no canary reached any envelope.

    uv run python tools/sentry_envelope_listener.py serve --port 9998 --out .envelopes/backend
    uv run python tools/sentry_envelope_listener.py check .envelopes/backend canary-a canary-b \
        --require event transaction

DSN for the app: http://public@127.0.0.1:9998/1
"""

from __future__ import annotations

import argparse
import gzip
import itertools
import json
import sys
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from collections.abc import Mapping

_ITEM_HEADER_KEYS = {"type", "length", "content_type", "filename", "attachment_type", "item_count"}


def read_body(stream: BinaryIO, headers: Mapping[str, str]) -> bytes:
    """The request body, sized or chunked. The Node SDK sends envelopes with
    Transfer-Encoding: chunked and no Content-Length."""
    if (headers.get("Transfer-Encoding") or "").lower() == "chunked":
        body = bytearray()
        while True:
            size = int(stream.readline().split(b";", 1)[0].strip(), 16)
            if size == 0:
                stream.readline()  # the blank line that ends the body
                return bytes(body)
            body += stream.read(size)
            stream.readline()  # the CRLF after each chunk
    return stream.read(int(headers.get("Content-Length") or 0))


def decode_body(body: bytes, encoding: str | None) -> bytes:
    """The envelope as the SDK built it, before content encoding."""
    if encoding in (None, "", "identity"):
        return body
    if encoding == "gzip":
        return gzip.decompress(body)
    if encoding == "deflate":
        return zlib.decompress(body)
    raise ValueError(f"unsupported content encoding: {encoding}")


def find_canaries(envelope: bytes, canaries: list[str]) -> list[str]:
    """The canaries that appear anywhere in an envelope."""
    return [canary for canary in canaries if canary.encode() in envelope]


def item_types(envelope: bytes) -> list[str]:
    """The item types in an envelope, read from its item headers."""
    types: list[str] = []
    for line in envelope.split(b"\n"):
        try:
            header = json.loads(line)
        except ValueError:
            continue
        if isinstance(header, dict) and "type" in header and set(header) <= _ITEM_HEADER_KEYS:
            types.append(str(header["type"]))
    return types


def serve(port: int, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    counter = itertools.count(1)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = read_body(self.rfile, self.headers)
            envelope = decode_body(body, self.headers.get("Content-Encoding"))
            (out / f"{next(counter):04d}.envelope").write_bytes(envelope)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *_args: object) -> None:
            return

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


def check(out: Path, canaries: list[str], require: list[str]) -> int:
    seen: set[str] = set()
    leaked = False
    for path in sorted(out.glob("*.envelope")):
        envelope = path.read_bytes()
        types = item_types(envelope)
        seen.update(types)
        found = find_canaries(envelope, canaries)
        print(f"{path.name}: {', '.join(types) or 'no items'}; canaries: {found or 'none'}")
        leaked = leaked or bool(found)
    missing = [kind for kind in require if kind not in seen]
    if missing:
        print(f"missing item types: {missing}")
    return 1 if leaked or missing else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    commands = parser.add_subparsers(dest="command", required=True)
    serve_cmd = commands.add_parser("serve")
    serve_cmd.add_argument("--port", type=int, default=9998)
    serve_cmd.add_argument("--out", type=Path, default=Path(".envelopes"))
    check_cmd = commands.add_parser("check")
    check_cmd.add_argument("out", type=Path)
    check_cmd.add_argument("canaries", nargs="+")
    check_cmd.add_argument("--require", nargs="*", default=[])
    args = parser.parse_args()
    if args.command == "serve":
        serve(args.port, args.out)
        return 0
    return check(args.out, args.canaries, args.require)


if __name__ == "__main__":
    sys.exit(main())
