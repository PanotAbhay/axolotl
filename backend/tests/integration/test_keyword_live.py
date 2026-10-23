"""T-06 keyword search on real Atlas, no Gemini key needed - owner: Dev 3.

`test_search_live.py` covers T-06 and T-07 together and needs a Gemini key for the
import. Keyword search needs none, so this proves T-06 on any machine with
`MONGODB_URI`: real chunks from the demo fixture, the real `code_chunks_text` index,
real Atlas scoring.

**Isolation.** One `axolotl_test_<random>` database for the module, dropped at the end
after asserting the prefix. Building the search index takes ~30 s, so it is built once.
"""

import asyncio
import secrets
import time

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient

from app import ingestion
from app.analysis.astwalk import analyse_module
from app.config import get_settings
from app.persistence import db
from app.search import search_repository
from app.search.indexes import CHUNKS_COLLECTION, ensure_search_indexes, search_status
from app.search.pipeline import index_repository

# One event loop for the module: the Atlas client is bound to the loop it was made on.
pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="module")]

TEST_DB_PREFIX = "axolotl_test_"
REPO = "repo_t06keyword001"
TIMEOUT_S = 180


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def repo_id():
    settings = get_settings()
    if not settings.mongodb_uri:
        pytest.skip("MONGODB_URI is not set - fill .env to run live tests")

    name = TEST_DB_PREFIX + secrets.token_hex(4)
    client = AsyncMongoClient(
        settings.mongodb_uri, serverSelectionTimeoutMS=10000,
        appname="axolotl-tests", tz_aware=True,
    )
    mp = pytest.MonkeyPatch()
    mp.setattr(db, "_client", client)
    mp.setattr(db, "_database_name", name)
    try:
        await client[name].create_collection(CHUNKS_COLLECTION)
        await ensure_search_indexes()

        deadline = time.monotonic() + TIMEOUT_S
        while (await search_status())["keyword"] != "ok":
            if time.monotonic() > deadline:
                pytest.fail(f"keyword index not ready after {TIMEOUT_S}s")
            await asyncio.sleep(2)

        root = ingestion.fixture_path("legacy_orders")
        analyses = [
            analyse_module(source_path=p, relative_path=p.relative_to(root).as_posix(),
                           repository_id=REPO, snapshot_hash="sha256:t06")
            for p in sorted(root.rglob("*.py"))
        ]
        # The real pipeline, minus the model calls: chunk, store, wait until searchable.
        result = await index_repository(
            REPO, [s for a in analyses for s in a.symbols],
            {a.module_id: a.source for a in analyses}, enrich=False,
        )
        assert result["chunks"] >= 20
        yield REPO
    finally:
        assert name.startswith(TEST_DB_PREFIX), f"refusing to drop {name!r}"
        try:
            await client.drop_database(name)
        finally:
            mp.undo()
            await client.close()


async def top(repo_id: str, query: str) -> list[str]:
    result = await search_repository(repo_id, query, mode="keyword", limit=3)
    assert result["mode_used"] == "keyword"
    return [hit.qualified_name for hit in result["hits"]]


@pytest.mark.parametrize(("query", "expected"), [
    ("finalise_amount", "pricing.finalise_amount"),
    ("finalise", "pricing.finalise_amount"),
    ("pricing.finalise_amount", "pricing.finalise_amount"),
    ("discount_rate", "pricing.discount_rate"),
    ("place_order", "orders.place_order"),
])
async def test_t06_an_exact_name_ranks_its_symbol_first(repo_id, query, expected):
    assert (await top(repo_id, query))[0] == expected


@pytest.mark.parametrize("error", [
    "quantity must not be negative",
    "quantity is required",
])
async def test_t06_an_error_string_finds_the_function_that_raises_it(repo_id, error):
    """Ahead of the test whose name happens to share two of the words."""
    assert (await top(repo_id, error))[0] == "pricing.line_gross"
