import logging
from collections.abc import AsyncIterator
from typing import Literal

from app.models import Report
from app.narrative.budget import DailyBudget
from app.narrative.cache import NarrativeCache
from app.narrative.fallback import fallback_narrative
from app.narrative.llm import FakeNarrativeLLM, NarrativeLLM
from app.narrative.prompts import build_messages

logger = logging.getLogger(__name__)

Mode = Literal["roast", "mentor"]

# Per-mode sampling. Roast wants surprise + edge; mentor wants directness.
_TEMPERATURE_BY_MODE: dict[Mode, float] = {
    "roast": 0.95,
    "mentor": 0.55,
}


class NarrativeService:
    """Orchestrates caching, daily budgeting, prompt construction, and LLM
    streaming."""

    def __init__(
        self,
        *,
        cache: NarrativeCache,
        budget: DailyBudget,
        llm: NarrativeLLM | FakeNarrativeLLM,
    ) -> None:
        self._cache = cache
        self._budget = budget
        self._llm = llm

    async def stream_narrative(
        self, mode: Mode, report: Report
    ) -> AsyncIterator[str]:
        # 1. Check cache
        cache_key = self._cache.key(
            report.username, self._cache.scores_hash(report), mode
        )
        cached = await self._cache.aget(cache_key)
        if cached is not None:
            logger.info(
                f"Narrative cache hit for {report.username} ({mode}, score={report.total})"
            )
            yield cached
            return

        # 2. Check budget
        allowed, _remaining, _resets_at = self._budget.try_consume()
        if not allowed:
            logger.warning(
                f"Daily OpenAI budget exhausted. Using fallback narrative for {report.username} ({mode})"
            )
            yield fallback_narrative(mode, report, reason="budget")
            return

        # 3. Stream from LLM
        messages = build_messages(mode, report)
        acc: list[str] = []
        try:
            async for chunk in self._llm.stream_chat(
                messages, temperature=_TEMPERATURE_BY_MODE[mode]
            ):
                acc.append(chunk)
                yield chunk
        except Exception as e:
            logger.error(
                f"LLM streaming failed for {report.username} ({mode}): {e}. Activating fallback narrative.",
                exc_info=True,
            )
            yield fallback_narrative(mode, report, reason="error")
            return

        # 4. Cache successful result
        full_text = "".join(acc)
        await self._cache.aput(cache_key, full_text)
