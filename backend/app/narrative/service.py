import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from app.models import Report
from app.narrative.budget import DailyBudget
from app.narrative.cache import NarrativeCache
from app.narrative.fallback import fallback_narrative
from app.narrative.llm import FakeNarrativeLLM, NarrativeLLM, StreamOutcome
from app.narrative.prompts import build_messages
from app.observability.narrative_health import record_narrative_fallback

logger = logging.getLogger(__name__)

Mode = Literal["roast", "mentor"]

# Per-mode sampling. Roast wants surprise + edge; mentor wants directness.
_TEMPERATURE_BY_MODE: dict[Mode, float] = {
    "roast": 0.95,
    "mentor": 0.55,
}


@dataclass
class NarrativeStreamMeta:
    """Per-stream metadata the caller owns and the service writes through.

    Lets the persistence layer record `is_fallback` honestly without breaking
    the iterator's `str` yield contract (SSE serializer stays unchanged).
    """

    is_fallback: bool = False
    fallback_reason: Literal["budget", "error"] | None = None
    cache_hit: bool = False
    # v1.0.5 SI-07: the UTC day a budget slot was consumed, so an abort refund
    # targets the correct day key across a midnight rollover.
    consumed_day: str | None = None
    # True when the model hit the completion ceiling mid-sentence. Previously
    # nothing downstream could tell a finished narrative from a guillotined one.
    truncated: bool = False


class NarrativeService:
    """Orchestrates caching, daily budgeting, prompt construction, and LLM
    streaming."""

    def __init__(
        self,
        *,
        cache: NarrativeCache,
        budget: DailyBudget,
        llm: NarrativeLLM | FakeNarrativeLLM,
        max_output_tokens: int = 1200,
        reasoning_effort: str | None = None,
    ) -> None:
        self._cache = cache
        self._budget = budget
        self._llm = llm
        self._max_output_tokens = max_output_tokens
        self._reasoning_effort = reasoning_effort

    async def stream_narrative(
        self,
        mode: Mode,
        report: Report,
        *,
        meta: NarrativeStreamMeta | None = None,
        subject: str | None = None,
        subject_limit: int | None = None,
    ) -> AsyncIterator[str]:
        # 1. Check cache
        cache_key = self._cache.key(report.username, self._cache.scores_hash(report), mode)
        cached = await self._cache.aget(cache_key)
        # Truthy, not `is not None`: an empty string cached by an earlier build
        # would otherwise be served as a hit for the rest of its 24h TTL.
        if cached:
            logger.info(f"Narrative cache hit for {report.username} ({mode}, score={report.total})")
            if meta is not None:
                meta.cache_hit = True
            yield cached
            return

        # 2. Check budget
        allowed, _remaining, _resets_at = await self._budget.atry_consume(
            subject=subject, subject_limit=subject_limit
        )
        if not allowed:
            record_narrative_fallback(reason="budget", mode=mode, username=report.username)
            if meta is not None:
                meta.is_fallback = True
                meta.fallback_reason = "budget"
            yield fallback_narrative(mode, report, reason="budget")
            return

        # Budget slot consumed — record the UTC day so an abort refund targets
        # the correct day key (v1.0.5 SI-07).
        if meta is not None:
            meta.consumed_day = datetime.now(UTC).strftime("%Y-%m-%d")

        # 3. Stream from LLM
        messages = build_messages(mode, report)
        acc: list[str] = []
        outcome = StreamOutcome()
        try:
            async for chunk in self._llm.stream_chat(
                messages,
                temperature=_TEMPERATURE_BY_MODE[mode],
                max_output_tokens=self._max_output_tokens,
                reasoning_effort=self._reasoning_effort,
                outcome=outcome,
            ):
                acc.append(chunk)
                yield chunk
        except Exception as e:
            logger.error(
                f"LLM streaming failed for {report.username} ({mode}): {e}. Activating fallback narrative.",
                exc_info=True,
            )
            record_narrative_fallback(
                reason="error", mode=mode, username=report.username, detail=repr(e)
            )
            if meta is not None:
                meta.is_fallback = True
                meta.fallback_reason = "error"
            yield fallback_narrative(mode, report, reason="error")
            return

        # 4. An empty completion is a failure, not a narrative. A reasoning
        # model can spend its entire completion budget thinking and emit no
        # prose at all; yielding nothing renders a blank card downstream.
        full_text = "".join(acc)
        if not full_text.strip():
            record_narrative_fallback(
                reason="error",
                mode=mode,
                username=report.username,
                detail=f"empty completion (finish_reason={outcome.finish_reason!r})",
            )
            if meta is not None:
                meta.is_fallback = True
                meta.fallback_reason = "error"
            yield fallback_narrative(mode, report, reason="error")
            return

        if outcome.truncated:
            logger.warning(
                f"Narrative truncated at the token ceiling for {report.username} ({mode}); "
                f"not caching a partial narrative."
            )
            if meta is not None:
                meta.truncated = True
            return

        # 5. Cache successful result
        await self._cache.aput(cache_key, full_text)

    async def refund(self, *, subject: str | None = None, consumed_day: str | None = None) -> None:
        """Refund a budget slot consumed by a stream the client aborted before
        completion (v1.0.5 SI-07)."""
        await self._budget.arefund(subject=subject, consumed_day=consumed_day)
