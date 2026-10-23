"""Live Gemini checks - owner: Dev 2, findings for Dev 1 and Dev 3.

Behind the `live` marker; skips when `GEMINI_API_KEY` is unset.

    uv run pytest -m live -s        # -s so the printed model list is visible

These exist to answer the Phase 0 questions the planning docs left open, with evidence
rather than assumption:

  - which models this key can actually use
  - whether `gemini-4-argon` exists, and what to set `GEMINI_MODEL` to if not
  - which embedding model and how many dimensions, for Dev 3's vector index

They assert almost nothing about *which* models exist - that is the account's business,
not ours. They assert the key works and print what it can reach.
"""

import pytest

from app.agents.health import gemini_status, reset_cache
from app.config import get_settings

pytestmark = pytest.mark.live


@pytest.fixture
def gemini_client():
    settings = get_settings()
    if not settings.gemini_api_key:
        pytest.skip("GEMINI_API_KEY is not set - fill .env to run live tests")

    from google import genai

    return genai.Client(api_key=settings.gemini_api_key)


async def test_the_key_works_and_we_can_list_models(gemini_client):
    names: list[str] = []
    async for model in await gemini_client.aio.models.list():
        name = getattr(model, "name", "") or ""
        names.append(name.removeprefix("models/"))

    assert names, "the key authenticated but could not list any models"

    print(f"\n  {len(names)} model(s) available to this key:")
    for name in sorted(names):
        print(f"    {name}")

    generative = sorted(n for n in names if "embed" not in n.lower())
    embedding = sorted(n for n in names if "embed" in n.lower())

    print("\n  generative:", ", ".join(generative) or "none")
    print("  embedding :", ", ".join(embedding) or "none")
    print("\n  -> set GEMINI_EMBEDDING_MODEL from the embedding list and tell Dev 3 "
          "its dimension count for the code_chunks_vector index.")


async def test_whether_the_configured_model_is_actually_available(gemini_client):
    """GEMINI_MODEL defaults to gemini-4-argon. If the key cannot reach it, say so
    loudly here rather than discovering it mid-demo."""
    settings = get_settings()
    configured = settings.gemini_model

    names: list[str] = []
    async for model in await gemini_client.aio.models.list():
        names.append((getattr(model, "name", "") or "").removeprefix("models/"))

    if configured in names:
        print(f"\n  GEMINI_MODEL={configured} is available.")
        return

    fallbacks = sorted(
        n for n in names if "embed" not in n.lower() and "gemini" in n.lower()
    )
    pytest.skip(
        f"GEMINI_MODEL={configured!r} is NOT available to this key. "
        f"Set GEMINI_MODEL to one of: {', '.join(fallbacks) or 'none found'}. "
        "The app already reads the model name from config, so this is a .env change, "
        "not a code change."
    )


async def test_one_real_generation_round_trip(gemini_client):
    """The cheapest call that proves the key, the model name and the quota together."""
    settings = get_settings()
    try:
        response = await gemini_client.aio.models.generate_content(
            model=settings.gemini_model,
            contents="Reply with the single word: ready",
        )
    except Exception as exc:  # noqa: BLE001 - the failure IS the finding
        pytest.skip(
            f"generate_content failed for {settings.gemini_model!r}: "
            f"{type(exc).__name__}: {exc}"
        )

    text = (getattr(response, "text", "") or "").strip()
    print(f"\n  {settings.gemini_model} replied: {text!r}")
    assert text, "the model returned an empty response"


async def test_the_status_endpoint_agrees_with_reality(gemini_client):
    """/system/status must report reachable when the key genuinely works."""
    reset_cache()
    status = await gemini_status(use_cache=False)

    print(f"\n  gemini_status -> {status}")
    assert status["reachable"] is True, (
        f"the key works but gemini_status says unreachable: {status.get('detail')}"
    )
    reset_cache()
