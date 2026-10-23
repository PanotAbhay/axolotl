"""Live persistence tests - owner: Dev 3. SHARED_CONTRACTS §9.

Real Atlas cluster, behind the `live` marker; skipped when `MONGODB_URI` is unset.

**Isolation.** Each test gets its own `axolotl_test_<random>` database, dropped at
the end after asserting the prefix. The real `axolotl` database is never touched.
"""

import secrets

import pytest
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError

from app.config import get_settings
from app.orchestration import events as events_module
from app.orchestration import store as store_module
from app.persistence import db
from app.persistence.indexes import COLLECTIONS, INDEX_SPECS, ensure_indexes
from app.search import search_status
from app.verification import store as verification_store

pytestmark = pytest.mark.live

TEST_DB_PREFIX = "axolotl_test_"


@pytest.fixture
async def live_db(monkeypatch):
    settings = get_settings()
    if not settings.mongodb_uri:
        pytest.skip("MONGODB_URI is not set - fill .env to run live tests")

    name = TEST_DB_PREFIX + secrets.token_hex(4)
    client = AsyncMongoClient(
        settings.mongodb_uri, serverSelectionTimeoutMS=10000,
        appname="axolotl-tests", tz_aware=True,
    )
    monkeypatch.setattr(db, "_client", client)
    monkeypatch.setattr(db, "_database_name", name)
    try:
        yield client[name]
    finally:
        assert name.startswith(TEST_DB_PREFIX), f"refusing to drop {name!r}"
        try:
            await client.drop_database(name)
        finally:
            await client.close()


async def _snapshot(database) -> dict[str, dict]:
    return {c: await database[c].index_information() for c in COLLECTIONS}


async def test_ping_reaches_atlas(live_db):
    ok, error = await db.ping()
    assert ok, error


async def test_ensure_indexes_creates_all_collections_and_indexes(live_db):
    report = await ensure_indexes()

    assert sorted(report.collections_created) == sorted(COLLECTIONS)
    assert len(report.indexes_created) == len(INDEX_SPECS)
    assert report.conflicts == []
    assert set(await live_db.list_collection_names()) >= set(COLLECTIONS)

    for spec in INDEX_SPECS:
        info = (await live_db[spec.collection].index_information()).get(spec.name)
        assert info is not None, f"missing {spec.collection}.{spec.name}"
        assert [(f, int(d)) for f, d in info["key"]] == list(spec.keys)
        assert bool(info.get("unique")) == spec.unique


async def test_ensure_indexes_twice_changes_nothing(live_db):
    await ensure_indexes()
    before = await _snapshot(live_db)

    second = await ensure_indexes()

    assert second.collections_created == []
    assert second.indexes_created == []
    assert second.conflicts == []
    assert len(second.indexes_present) == len(INDEX_SPECS)
    assert await _snapshot(live_db) == before


async def _other_owners_ensure_indexes() -> None:
    await store_module.ensure_indexes()
    await events_module.ensure_indexes()
    await verification_store.ensure_indexes()


async def test_coexists_with_other_owners_index_functions_in_either_order(live_db):
    """main.py's lifespan also runs Dev 2's and Dev 4's ensure_indexes; none may break."""
    await _other_owners_ensure_indexes()

    report = await ensure_indexes()
    assert report.conflicts == []
    theirs = {"migration_plans", "migration_runs", "run_events", "artefacts",
              "verification_results", "counterexamples"}
    assert not [label for label in report.indexes_created if label.split(".")[0] in theirs]

    await _other_owners_ensure_indexes()  # and the other way round


async def test_an_existing_index_is_never_modified(live_db):
    """Same keys under another name: reported, left alone, startup carries on."""
    await live_db["repositories"].create_index(
        "repository_id", unique=True, name="someone_elses_name"
    )

    report = await ensure_indexes()

    assert any("repositories.repository_id_unique" in c for c in report.conflicts)
    info = await live_db["repositories"].index_information()
    assert "repository_id_unique" not in info  # no duplicate created
    assert info["someone_elses_name"]["key"] == [("repository_id", 1)]
    assert info["someone_elses_name"].get("unique") is True  # untouched


async def test_unique_indexes_really_reject_duplicates(live_db):
    await ensure_indexes()
    await live_db["symbols"].insert_one({"repository_id": "repo_a", "symbol_id": "sym_1"})
    # Same symbol id in another repository is fine...
    await live_db["symbols"].insert_one({"repository_id": "repo_b", "symbol_id": "sym_1"})
    # ...but not twice in the same one.
    with pytest.raises(DuplicateKeyError):
        await live_db["symbols"].insert_one({"repository_id": "repo_a", "symbol_id": "sym_1"})


async def test_search_status_is_honestly_unavailable_without_search_indexes(live_db):
    await ensure_indexes()
    assert await search_status() == {"keyword": "unavailable", "vector": "unavailable"}


async def test_symbols_are_linked_to_their_chunks(live_db):
    from app.persistence import graphstore

    await ensure_indexes()
    await live_db["symbols"].insert_many([
        {"repository_id": "repo_a", "symbol_id": "sym_1", "source_chunk_id": "stale"},
        {"repository_id": "repo_a", "symbol_id": "sym_2", "source_chunk_id": "stale"},
        {"repository_id": "repo_b", "symbol_id": "sym_1", "source_chunk_id": "keep"},
    ])

    await graphstore.set_source_chunk_ids("repo_a", {"sym_1": "chunk_1"})

    by_id = {
        (d["repository_id"], d["symbol_id"]): d["source_chunk_id"]
        async for d in live_db["symbols"].find({}, {"_id": 0})
    }
    assert by_id == {
        ("repo_a", "sym_1"): "chunk_1",
        ("repo_a", "sym_2"): None,     # no chunk any more: cleared, not left stale
        ("repo_b", "sym_1"): "keep",   # another repository is never touched
    }
