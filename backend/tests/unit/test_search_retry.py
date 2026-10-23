"""Retrying transient model failures - owner: Dev 3. Offline.

Written after a real import lost all forty descriptions to
`503 UNAVAILABLE - "This model is currently experiencing high demand"`. The code was
fine; the model was busy. These tests pin what is retried, what is not, and that a
failure still says what went wrong.
"""

import asyncio

import pytest

from app.search.retry import describe, is_retryable, with_retries

pytestmark = pytest.mark.anyio


class Busy(Exception):
    """Shaped like the google-genai error that actually happened."""

    def __init__(self) -> None:
        super().__init__(
            "503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is "
            "currently experiencing high demand.', 'status': 'UNAVAILABLE'}}"
        )
        self.code = 503


class BadRequest(Exception):
    def __init__(self) -> None:
        super().__init__("400 INVALID_ARGUMENT. Unknown field 'nonsense'")
        self.code = 400


def test_a_busy_model_is_retryable():
    assert is_retryable(Busy())
    assert is_retryable(TimeoutError("deadline exceeded"))
    assert is_retryable(Exception("429 RESOURCE_EXHAUSTED"))
    assert is_retryable(Exception("The model is overloaded"))


def test_a_bad_request_is_not_retryable():
    """Repeating it would spend quota to get the same answer."""
    assert not is_retryable(BadRequest())
    assert not is_retryable(Exception("404 NOT_FOUND. Model does not exist"))
    assert not is_retryable(ValueError("embedding dimensions must match"))


def test_a_failure_says_what_went_wrong():
    message = describe(Busy())
    assert message.startswith("Busy: ")
    assert "503" in message
    assert "high demand" in message
    # Collapsed to one line, so it stays readable in a warnings list.
    assert "\n" not in message


def test_a_message_is_truncated_rather_than_flooding_the_warnings():
    assert len(describe(Exception("x" * 1000), limit=50)) <= 50 + len("Exception: ")


def test_an_exception_with_no_message_still_names_its_type():
    assert describe(Exception()) == "Exception"


async def test_a_transient_failure_is_retried_until_it_succeeds(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    attempts = {"n": 0}

    async def call() -> str:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise Busy()
        return "described"

    assert await with_retries(call, what="description") == "described"
    assert attempts["n"] == 3


async def test_a_permanent_failure_is_not_retried(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    attempts = {"n": 0}

    async def call() -> str:
        attempts["n"] += 1
        raise BadRequest()

    with pytest.raises(BadRequest):
        await with_retries(call, what="description")
    assert attempts["n"] == 1


async def test_retries_give_up_and_raise_the_last_failure(monkeypatch):
    """Giving up loudly beats returning something invented."""
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    attempts = {"n": 0}

    async def call() -> str:
        attempts["n"] += 1
        raise Busy()

    with pytest.raises(Busy):
        await with_retries(call, what="description", attempts=3)
    assert attempts["n"] == 3


async def test_backoff_grows_and_is_jittered(monkeypatch):
    """Jitter matters: forty chunks failing together must not retry in lockstep."""
    delays: list[float] = []

    async def record(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", record)

    async def call() -> str:
        raise Busy()

    with pytest.raises(Busy):
        await with_retries(call, what="description", attempts=4)

    assert len(delays) == 3
    # Each window is twice the last, and the jitter keeps every value inside it.
    for index, delay in enumerate(delays):
        base = 2.0 ** index
        assert 0.5 * base <= delay <= 1.5 * base


async def _no_sleep(_seconds: float) -> None:
    return None
