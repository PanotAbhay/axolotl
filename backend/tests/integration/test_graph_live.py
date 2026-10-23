"""The graph round trip through real Atlas - owner: Dev 3. T-01, T-03, T-04 live.

The unit tests prove parsing and graph building with Atlas replaced by an in-memory
stand-in. This proves the claim the MongoDB bounty rests on: the graph **lives in
Atlas**. The real import writes the demo fixture's repository, symbols and edges to a
real database, and every read the UI and scheduler use (`get_repository`, `get_graph`,
`load_networkx`, `get_module_detail`, `get_symbol`, `find_symbol`) reads them back.

**Isolation.** One `axolotl_test_<random>` database for the module, dropped at the end
after asserting the prefix; the snapshot goes to a temporary folder. Search enrichment
is off and the wait for Atlas Search is skipped: this file is about the graph, and the
throwaway database has no search index to wait for.
"""

import secrets
from datetime import datetime

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient

from app import graph, ingestion
from app.config import get_settings
from app.errors import AppError
from app.persistence import db, graphstore
from app.persistence.indexes import ensure_indexes
from app.search import pipeline

# One event loop for the module: the Atlas client is bound to the loop it was made on.
pytestmark = [pytest.mark.live, pytest.mark.asyncio(loop_scope="module")]

TEST_DB_PREFIX = "axolotl_test_"

# demo/legacy_orders/README.md. A -> B means A depends on B.
T03_EDGES = {
    ("module_main", "module_orders"),
    ("module_main", "module_refunds"),
    ("module_orders", "module_pricing"),
    ("module_orders", "module_customers"),
    ("module_orders", "module_storage"),
    ("module_refunds", "module_pricing"),
    ("module_refunds", "module_storage"),
}
LOCAL_MODULES = {
    "module_main", "module_orders", "module_refunds",
    "module_pricing", "module_customers", "module_storage",
}


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def imported(tmp_path_factory):
    settings = get_settings()
    if not settings.mongodb_uri:
        pytest.skip("MONGODB_URI is not set - fill .env to run live tests")

    name = TEST_DB_PREFIX + secrets.token_hex(4)
    snapshots = tmp_path_factory.mktemp("snapshots")
    client = AsyncMongoClient(
        settings.mongodb_uri, serverSelectionTimeoutMS=10000,
        appname="axolotl-tests", tz_aware=True,
    )

    async def searchable(repository_id, **_):
        return True

    mp = pytest.MonkeyPatch()
    mp.setattr(db, "_client", client)
    mp.setattr(db, "_database_name", name)
    mp.setattr(ingestion, "snapshot_path", lambda repo_id: snapshots / repo_id)
    mp.setattr(settings, "index_on_import", False)
    mp.setattr(pipeline, "wait_until_searchable", searchable)
    try:
        await ensure_indexes()
        record = await ingestion.import_repository(demo_fixture_id="legacy_orders")
        yield {"record": record, "database": client[name], "snapshots": snapshots}
    finally:
        assert name.startswith(TEST_DB_PREFIX), f"refusing to drop {name!r}"
        try:
            await client.drop_database(name)
        finally:
            mp.undo()
            await client.close()


def repo(imported) -> str:
    return imported["record"].repository_id


# --------------------------------------------------------------------------
# T-01: the import reached Atlas
# --------------------------------------------------------------------------

async def test_t01_the_repository_record_round_trips(imported):
    stored = await graphstore.get_repository(repo(imported))
    original = imported["record"]
    assert stored.model_dump(exclude={"created_at"}) == original.model_dump(
        exclude={"created_at"}
    )
    # BSON dates are millisecond precision: microseconds do not survive the round trip.
    assert stored.created_at == original.created_at.replace(
        microsecond=original.created_at.microsecond // 1000 * 1000
    )
    assert stored.analysis_status == "ok"
    assert (stored.module_count, stored.symbol_count) == (7, 40)
    assert isinstance(stored.created_at, datetime) and stored.created_at.tzinfo is not None


async def test_t01_symbols_and_edges_are_real_documents(imported):
    database = imported["database"]
    assert await database["symbols"].count_documents({"repository_id": repo(imported)}) == 40
    edge = await database["edges"].find_one({"repository_id": repo(imported)})
    # docs/mongodb-atlas.md, "Deviations from §9": stored as source/target.
    assert {"source", "target", "type", "resolution", "basis"} <= set(edge)


# --------------------------------------------------------------------------
# T-03: the scheduling graph, rebuilt from Atlas
# --------------------------------------------------------------------------

async def test_t03_load_networkx_from_atlas_is_exactly_the_expected_edges(imported):
    scheduling = await graph.load_networkx(repo(imported))
    assert set(scheduling.edges()) == T03_EDGES
    assert set(scheduling.nodes()) == LOCAL_MODULES


async def test_t03_the_ui_graph_from_atlas_has_every_local_module_and_edge(imported):
    payload = await graph.get_graph(repo(imported))
    nodes = {n.id: n for n in payload.nodes}

    assert LOCAL_MODULES <= set(nodes)
    assert nodes["module_tests__test_baseline"].kind == "test_module"
    assert nodes["ext_decimal"].kind == "external_package"
    dependency_edges = {
        (e.source, e.target) for e in payload.edges
        if e.type in {"imports", "from_imports"} and e.target in LOCAL_MODULES
        and e.source in LOCAL_MODULES
    }
    assert dependency_edges == T03_EDGES
    assert all(n.status == "not_planned" for n in payload.nodes)
    assert payload.snapshot_hash == imported["record"].snapshot_hash


async def test_t03_function_counts_come_from_the_stored_symbols(imported):
    nodes = {n.id: n for n in (await graph.get_graph(repo(imported))).nodes}
    # pricing.py: discount_rate, line_gross, finalise_amount
    assert nodes["module_pricing"].function_count == 3


# --------------------------------------------------------------------------
# T-04: symbol inspection, from Atlas plus the snapshot
# --------------------------------------------------------------------------

async def test_t04_module_detail_for_pricing(imported):
    detail = await graph.get_module_detail(repo(imported), "module_pricing")

    names = {s.qualified_name for s in detail.symbols}
    assert {"pricing", "pricing.finalise_amount", "pricing.line_gross"} <= names
    assert {e.target for e in detail.imports} == {"ext_decimal"}
    importers = {e.source for e in detail.dependants if e.type == "imports"}
    assert {"module_orders", "module_refunds"} <= importers
    expected = (ingestion.fixture_path("legacy_orders") / "pricing.py").read_text()
    assert detail.source == expected


async def test_t04_a_symbol_comes_back_with_exactly_its_source_lines(imported):
    found = await graph.find_symbol(repo(imported), "pricing.finalise_amount")
    assert found is not None

    record, source = await graph.get_symbol(repo(imported), found.symbol_id)
    assert record.symbol_id == found.symbol_id
    assert source.startswith("def finalise_amount(lines, category):")
    assert source.count("\n") + 1 == record.end_line - record.start_line + 1


async def test_every_symbol_points_at_a_stored_chunk(imported):
    database = imported["database"]
    chunk_ids = {c["chunk_id"] async for c in database["code_chunks"].find(
        {"repository_id": repo(imported)}, {"chunk_id": 1})}
    symbols = [s async for s in database["symbols"].find({"repository_id": repo(imported)})]
    linked = [s for s in symbols if s.get("source_chunk_id")]
    assert linked, "no symbol was linked to a chunk"
    assert {s["source_chunk_id"] for s in linked} <= chunk_ids


# --------------------------------------------------------------------------
# honest failures
# --------------------------------------------------------------------------

async def test_an_unknown_repository_is_a_404_not_an_empty_graph(imported):
    for read in (graph.get_graph, graphstore.get_repository):
        with pytest.raises(AppError) as caught:
            await read("repo_doesnotexist")
        assert caught.value.status_code == 404


async def test_an_unknown_module_is_a_404(imported):
    with pytest.raises(AppError) as caught:
        await graph.get_module_detail(repo(imported), "module_nope")
    assert caught.value.status_code == 404


# --------------------------------------------------------------------------
# a snapshot that is not on this machine
# --------------------------------------------------------------------------

async def test_with_the_snapshot_present_there_is_no_source_warning(imported):
    detail = await graph.get_module_detail(repo(imported), "module_pricing")
    assert graph.SOURCE_UNAVAILABLE not in detail.warnings

    found = await graph.find_symbol(repo(imported), "pricing.finalise_amount")
    _, source, warnings = await graph.get_symbol_detail(repo(imported), found.symbol_id)
    assert source and warnings == []


async def test_a_missing_snapshot_is_reported_not_shown_as_an_empty_file(imported):
    """Atlas has the graph; the snapshot is on another machine's disk."""
    snapshot = imported["snapshots"] / repo(imported)
    parked = snapshot.with_name(snapshot.name + ".parked")
    snapshot.rename(parked)
    try:
        detail = await graph.get_module_detail(repo(imported), "module_pricing")
        assert detail.source == ""
        assert graph.SOURCE_UNAVAILABLE in detail.warnings
        # The graph itself still comes from Atlas.
        assert {s.qualified_name for s in detail.symbols} >= {"pricing.finalise_amount"}

        found = await graph.find_symbol(repo(imported), "pricing.finalise_amount")
        record, source, warnings = await graph.get_symbol_detail(
            repo(imported), found.symbol_id
        )
        assert (source, warnings) == ("", [graph.SOURCE_UNAVAILABLE])
        assert record.qualified_name == "pricing.finalise_amount"
    finally:
        parked.rename(snapshot)
