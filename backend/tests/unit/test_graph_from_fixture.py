"""Graph construction against the real demo fixture - owner: Dev 3.

Covers T-01 (import and parse), T-03 (exact edge set) and T-04 (symbol inspection).

These analyse `demo/legacy_orders` **on disk** rather than a synthetic tree, so they
fail if the fixture and the graph ever drift apart. No database is involved: parsing
and graph construction are pure.

T-03 is the one that matters most. A graph with an invented edge would migrate things
in the wrong order; a graph missing one would migrate through an unverified
dependency. So it asserts the exact set - no extra, no missing, correct direction.
"""

import pytest

from app.analysis.astwalk import analyse_module
from app.analysis.identifiers import module_id_for
from app.graph.builder import (
    add_test_target_edges,
    build_edges,
    build_nodes,
    to_networkx,
)
from app.ingestion import fixture_path
from app.ingestion.safety import is_ignored

SNAPSHOT_HASH = "sha256:test"
REPOSITORY_ID = "repo_fixture0001"

# From demo/legacy_orders/README.md. A -> B means A depends on B.
EXPECTED_EDGES = {
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


@pytest.fixture(scope="module")
def analyses():
    root = fixture_path("legacy_orders")
    if not root.is_dir():
        pytest.skip(f"demo fixture not found at {root}")

    found = {}
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        if is_ignored(relative):
            continue
        analysis = analyse_module(
            source_path=path, relative_path=relative,
            repository_id=REPOSITORY_ID, snapshot_hash=SNAPSHOT_HASH,
        )
        found[analysis.module_id] = analysis
    return found


@pytest.fixture(scope="module")
def graph(analyses):
    nodes = build_nodes(analyses)
    edges, external_nodes, warnings = build_edges(analyses)
    edges = add_test_target_edges(analyses, edges)
    return {
        "nodes": nodes + external_nodes,
        "edges": edges,
        "warnings": warnings,
        "scheduling": to_networkx(nodes + external_nodes, edges),
    }


# --------------------------------------------------------------------------
# T-01: import and parse
# --------------------------------------------------------------------------

def test_every_fixture_module_parses(analyses):
    """T-01: successful AST parse across the fixture."""
    failed = [a.path for a in analyses.values() if not a.parsed]
    assert not failed, f"these did not parse: {failed}"


def test_the_fixture_has_the_six_modules_plus_its_test_module(analyses):
    local = {m for m, a in analyses.items() if not a.is_test}
    tests = {m for m, a in analyses.items() if a.is_test}

    assert local == LOCAL_MODULES
    assert tests == {module_id_for("tests/test_baseline.py")}


def test_no_warnings_from_a_clean_fixture(analyses):
    warnings = [w for a in analyses.values() for w in a.warnings]
    assert warnings == [], f"the fixture should parse cleanly: {warnings}"


# --------------------------------------------------------------------------
# T-03: the exact edge set
# --------------------------------------------------------------------------

def test_the_scheduling_graph_has_exactly_the_expected_edges(graph):
    """T-03: no extra, no missing, correct direction."""
    actual = set(graph["scheduling"].edges())

    assert actual == EXPECTED_EDGES, (
        f"unexpected: {sorted(actual - EXPECTED_EDGES)}; "
        f"missing: {sorted(EXPECTED_EDGES - actual)}"
    )


def test_the_scheduling_graph_holds_only_local_modules(graph):
    assert set(graph["scheduling"].nodes()) == LOCAL_MODULES


def test_edge_direction_is_dependant_to_dependency(graph):
    """orders imports pricing, so orders -> pricing. Backwards would invert the
    whole migration order."""
    scheduling = graph["scheduling"]
    assert scheduling.has_edge("module_orders", "module_pricing")
    assert not scheduling.has_edge("module_pricing", "module_orders")


def test_pricing_is_a_leaf_and_main_depends_on_nothing_downstream(graph):
    scheduling = graph["scheduling"]
    assert list(scheduling.successors("module_pricing")) == []
    assert list(scheduling.predecessors("module_main")) == []


def test_the_fixture_graph_is_acyclic(graph):
    import networkx as nx

    assert nx.is_directed_acyclic_graph(graph["scheduling"]), (
        "the demo fixture must not contain a cycle; the cycle case is a separate "
        "fixture for T-05"
    )


def test_test_modules_are_excluded_from_scheduling(graph):
    """Test files are never migrated, so they must not appear in the scheduler."""
    test_module = module_id_for("tests/test_baseline.py")
    assert test_module not in graph["scheduling"].nodes()


def test_test_targets_edges_are_recorded_but_not_scheduled(graph):
    test_module = module_id_for("tests/test_baseline.py")
    targets = {
        e.target for e in graph["edges"]
        if e.type == "test_targets" and e.source == test_module
    }
    assert "module_pricing" in targets
    assert "module_orders" in targets
    # ...but they carry no weight in the scheduling graph.
    assert test_module not in graph["scheduling"].nodes()


def test_standard_library_imports_become_external_nodes(graph):
    external = {n.id for n in graph["nodes"] if n.kind == "external_package"}
    assert "ext_decimal" in external, "pricing.py imports decimal"
    assert all(n.startswith("ext_") for n in external)


def test_external_packages_are_never_scheduled(graph):
    assert not any(n.startswith("ext_") for n in graph["scheduling"].nodes())


def test_edges_are_deduped_per_module_pair(graph):
    pairs = [(e.source, e.target, e.type) for e in graph["edges"]]
    assert len(pairs) == len(set(pairs)), "an edge was recorded twice"


# --------------------------------------------------------------------------
# T-04: symbol inspection
# --------------------------------------------------------------------------

def test_the_seeded_rounding_function_is_found_with_its_line_span(analyses):
    """T-04: functions and source lines match the fixture."""
    pricing = analyses["module_pricing"]
    finalise = next(
        (s for s in pricing.symbols if s.qualified_name == "pricing.finalise_amount"),
        None,
    )

    assert finalise is not None, "finalise_amount was not extracted"
    assert finalise.kind == "function"
    assert finalise.start_line < finalise.end_line
    assert finalise.signature and "lines" in finalise.signature
    assert finalise.docstring and "stages" in finalise.docstring.lower()

    # The span must actually bracket the function in the real file.
    source_lines = pricing.source.splitlines()
    assert "def finalise_amount" in source_lines[finalise.start_line - 1]


def test_public_entry_points_are_extracted(analyses):
    orders = {s.qualified_name for s in analyses["module_orders"].symbols}
    refunds = {s.qualified_name for s in analyses["module_refunds"].symbols}
    assert "orders.place_order" in orders
    assert "refunds.partial_refund" in refunds


def test_every_module_gets_a_module_symbol(analyses):
    for module_id, analysis in analyses.items():
        kinds = [s.kind for s in analysis.symbols]
        assert kinds.count("module") == 1, f"{module_id} has {kinds.count('module')}"


def test_symbol_ids_are_deterministic(analyses):
    """Re-analysing the same file must produce the same ids, or a run's references
    would break on reimport."""
    root = fixture_path("legacy_orders")
    again = analyse_module(
        source_path=root / "pricing.py", relative_path="pricing.py",
        repository_id=REPOSITORY_ID, snapshot_hash=SNAPSHOT_HASH,
    )
    first = {s.symbol_id for s in analyses["module_pricing"].symbols}
    second = {s.symbol_id for s in again.symbols}
    assert first == second


def test_a_docstring_carrying_an_injection_is_stored_as_inert_data(analyses):
    """T-18 adjacent: customers.py holds a prompt-injection string as test data.

    It must be captured verbatim as a docstring - data to display, never an
    instruction. This asserts it survives extraction unchanged.
    """
    customers = analyses["module_customers"]
    category_for = next(
        s for s in customers.symbols if s.qualified_name == "customers.category_for"
    )
    assert "ignore previous instructions" in (category_for.docstring or "")
