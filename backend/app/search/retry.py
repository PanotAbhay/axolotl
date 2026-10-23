"""Retrying a transient model call - owner: Dev 3.

`gemini-3.8-flash` returned `503 UNAVAILABLE - "This model is currently experiencing
high demand"` for all forty description calls of one import. Nothing was wrong with
the code, the key or the prompt; the model was busy. Without retries a spike during
the demo means zero descriptions and visibly worse search.

Retried: 429 (rate limited), 500, 502, 503, 504, and timeouts. Not retried: 400, 403,
404 and anything else that says the request itself is wrong - repeating it would waste
quota to get the same answer.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 4
BASE_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 16.0

RETRYABLE_CODES = (429, 500, 502, 503, 504)
RETRYABLE_TEXT = (
    "unavailable", "high demand", "overloaded", "deadline exceeded",
    "resource_exhausted", "timeout", "temporarily",
)


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, asyncio.TimeoutError | TimeoutError):
        return True

    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int) and code in RETRYABLE_CODES:
        return True

    text = str(exc).lower()
    if any(str(c) in text for c in RETRYABLE_CODES) and "error" in text:
        return True
    return any(fragment in text for fragment in RETRYABLE_TEXT)


def describe(exc: BaseException, limit: int = 160) -> str:
    """`type: message`, truncated.

    The first version of this logged the exception type alone, which turned a
    diagnosable "503, the model is busy" into an opaque "ClientError" and cost a
    round of guessing.
    """
    message = " ".join(str(exc).split())
    return f"{type(exc).__name__}: {message[:limit]}" if message else type(exc).__name__


async def with_retries[T](
    call: Callable[[], Awaitable[T]], *, what: str, attempts: int = MAX_ATTEMPTS
) -> T:
    """Run `call`, retrying transient failures with jittered exponential backoff."""
    last: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await call()
        except Exception as exc:  # noqa: BLE001 - re-raised below
            last = exc
            if attempt == attempts or not is_retryable(exc):
                raise
            delay = min(BASE_DELAY_SECONDS * 2 ** (attempt - 1), MAX_DELAY_SECONDS)
            # Jittered, so forty chunks failing together do not all retry in step and
            # recreate the spike that caused the failure.
            delay *= 0.5 + random.random()  # noqa: S311 - backoff jitter, not crypto
            log.info("%s failed (%s); retrying in %.1fs [%d/%d]",
                     what, describe(exc, 80), delay, attempt, attempts)
            await asyncio.sleep(delay)

    raise AssertionError("unreachable") from last
