"""SSE keepalive helper for streaming responses.

Wraps an async iterator of dict events and injects periodic keepalive
events when no real events have been yielded for a configurable interval.
This prevents intermediate proxies (Cloud Run, Vercel, browsers) from
timing out idle SSE connections during long model reasoning phases.
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)

DEFAULT_KEEPALIVE_INTERVAL: float = 20  # seconds
DEFAULT_KEEPALIVE_TEXT = "📊 考え中…"


class _Sentinel:
    """Base sentinel for queue signalling."""


class _DoneSentinel(_Sentinel):
    """Signals that the upstream iterator has been exhausted."""


class _ExceptionSentinel(_Sentinel):
    """Carries an exception raised by the upstream iterator."""

    def __init__(self, exc: BaseException) -> None:
        self.exc = exc


async def with_keepalive(
    events: AsyncIterator[dict],
    *,
    interval: float = DEFAULT_KEEPALIVE_INTERVAL,
    text: str = DEFAULT_KEEPALIVE_TEXT,
) -> AsyncIterator[dict]:
    """Wrap an event stream, injecting keepalive dict events
    whenever *interval* seconds pass without a real event.

    The keepalive stops as soon as the underlying iterator is exhausted
    or the wrapping generator is closed (e.g. client disconnect /
    ``GeneratorExit``).
    """

    event_queue: asyncio.Queue[dict | _Sentinel] = asyncio.Queue()
    done = asyncio.Event()

    async def _pump() -> None:
        """Read from the upstream iterator and push into the queue."""
        try:
            async for event in events:
                await event_queue.put(event)
        except GeneratorExit:
            pass
        except Exception as exc:
            await event_queue.put(_ExceptionSentinel(exc))
        finally:
            done.set()
            await event_queue.put(_DoneSentinel())

    pump_task = asyncio.create_task(_pump())

    try:
        while True:
            try:
                item = await asyncio.wait_for(
                    event_queue.get(), timeout=interval
                )
            except asyncio.TimeoutError:
                if done.is_set():
                    break
                logger.debug("Sending SSE keepalive (no event for %.0fs)", interval)
                yield {"type": "keepalive", "text": text}
                continue

            if isinstance(item, _DoneSentinel):
                break
            if isinstance(item, _ExceptionSentinel):
                raise item.exc
            yield item
    finally:
        pump_task.cancel()
        try:
            await pump_task
        except asyncio.CancelledError:
            pass
