"""Unit tests for the `narratives.provider` derivation in the route layer.

v0.8.4 fix: previously the SSE persistence path hardcoded `provider="openai"`,
which silently mislabeled every Groq narrative in production. The new helper
maps `NARRATIVE_BASE_URL` to a stable provider tag.
"""

from __future__ import annotations

import pytest

from app.routers.narrative import _resolve_provider


@pytest.mark.parametrize(
    "base_url, expected",
    [
        (None, "openai"),
        ("", "openai"),
        ("https://api.openai.com/v1", "openai"),
        ("https://oai.openai.com/v1", "openai"),
        ("https://api.groq.com/openai/v1", "groq"),
        ("https://api.openrouter.ai/api/v1", "openrouter"),
        ("https://api.cerebras.ai/v1", "cerebras"),
        ("https://my-vllm.internal:8000/v1", "openai-compatible"),
        ("https://localhost:11434/v1", "openai-compatible"),
    ],
)
def test_resolve_provider(base_url: str | None, expected: str) -> None:
    assert _resolve_provider(base_url) == expected
