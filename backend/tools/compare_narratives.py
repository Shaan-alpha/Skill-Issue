"""Side-by-side narrative comparison across Groq models.

Hits a target GitHub username through the real ingestion + scoring pipeline,
then runs both Roast and Mentor prompts through each candidate Groq model
and prints the outputs to stdout for human comparison.

Usage (run from backend/):

    $env:GROQ_API_KEY = "<your gsk_... key>"
    $env:GITHUB_TOKEN = "<your gh_... token>"   # optional but recommended
    uv run python tools/compare_narratives.py octocat

The script does NOT touch the production deployment. Everything is local.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Run-from-anywhere: prepend backend/ to sys.path so `from app...` resolves
# without requiring `pythonpath = ["."]` (which only applies to pytest).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.github.client import GitHubClient
from app.ingestion.profile import ingest_profile
from app.narrative.llm import NarrativeLLM
from app.narrative.prompts import build_messages
from app.scoring.engine import run_scoring_engine

# (model_id, roast_temperature, mentor_temperature)
# Groq's current production-grade chat models as of 2026-08. Groq retires
# models on a rolling basis — deepseek-r1 and qwen-qwq went first, then
# llama-3.3-70b-versatile on 2026-08-16. Re-check console.groq.com/docs/models
# before trusting this list.
CANDIDATES: list[tuple[str, float, float]] = [
    ("openai/gpt-oss-120b", 0.95, 0.55),
    ("meta-llama/llama-4-maverick-17b-128e-instruct", 0.95, 0.55),
    ("moonshotai/kimi-k2-instruct-0905", 0.95, 0.55),
]


def _strip_reasoning(text: str) -> str:
    """Reasoning models (deepseek-r1, qwen-qwq) emit <think>...</think> blocks
    before their answer. Strip those so we judge only the user-facing output."""
    while "<think>" in text and "</think>" in text:
        a = text.index("<think>")
        b = text.index("</think>", a) + len("</think>")
        text = text[:a] + text[b:]
    return text.strip()


async def _stream_one(
    model: str, temperature: float, messages: list[dict[str, str]], api_key: str
) -> str:
    llm = NarrativeLLM(
        api_key=api_key,
        model=model,
        base_url="https://api.groq.com/openai/v1",
    )
    out: list[str] = []
    try:
        async for chunk in llm.stream_chat(messages, temperature=temperature):
            out.append(chunk)
    except Exception as exc:
        return f"[ERROR] {exc.__class__.__name__}: {exc}"
    return _strip_reasoning("".join(out))


async def main(username: str) -> None:
    groq_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not groq_key:
        sys.exit("GROQ_API_KEY (or OPENAI_API_KEY) must be set")

    gh_token = os.environ.get("GITHUB_TOKEN")
    print(f"Ingesting + scoring {username}…", file=sys.stderr)
    async with GitHubClient(token=gh_token) as gh:
        profile = await ingest_profile(username, gh)
        report = await run_scoring_engine(profile, gh)
    print(
        f"Done. Tier={report.tier.name}, score={report.total}, "
        f"badges={[b.slug for b in report.badges]}",
        file=sys.stderr,
    )

    for mode in ("roast", "mentor"):
        msgs = build_messages(mode, report)  # type: ignore[arg-type]
        for model, roast_t, mentor_t in CANDIDATES:
            temp = roast_t if mode == "roast" else mentor_t
            print("\n" + "=" * 78)
            print(f"MODE: {mode.upper():<6} MODEL: {model:<32} TEMP: {temp}")
            print("=" * 78)
            text = await _stream_one(model, temp, msgs, groq_key)
            print(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("username", help="GitHub username to analyse")
    args = parser.parse_args()
    asyncio.run(main(args.username))
