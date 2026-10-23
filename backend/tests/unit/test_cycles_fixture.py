"""T-05: cyclic dependency fixture - owner: Dev 3. Spec §5.4, §11.1.

"Cyclic dependency fixture -> SCC detected and grouped/flagged."

`tests/fixtures/cycles/` is a tiny package with two **real** import cycles, parsed by the
same AST and graph code as any import and grouped by Dev 2's real scheduler. Nothing in
it is executed. See its README for the expected edges.

  cycle 1  alpha <-> beta              absolute imports (`import` one way,
                                       `from ... import` the other)
  cycle 2  shop.cart <-> shop.tax      relative imports inside a package
  gamma -> alpha                       depends on cycle 1 from outside it
  gamma ~> beta                        importlib.import_module: unresolved, and must
                                       never join or create a cycle
"""

from pathlib import Path

import networkx as nx
import pytest

from app.analysis.astwalk import analyse_module
from app.graph.builder import build_edges, build_nodes, to_networkx
from app.orchestration.scheduler import build_units, eligible_units

ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "cycles"
REPOSITORY_ID = "repo_t05000000001"
SNAPSHOT_HASH = "sha256:t05"

# A -> B means A imports B. Local modules only.
EXPECTED_EDGES = {
    ("module_alpha", "module_beta"),
    ("module_beta", "module_alpha"),
    ("module_beta", "module_leaf"),
    ("module_gamma", "module_alpha"),
    ("module_shop__cart", "module_shop__tax"),
    ("module_shop__tax", "module_shop__cart"),
}
EXPECTED_CYCLES = [
    {"module_alpha", "module_beta"},
    {"module_shop__cart", "module_shop__tax"},
]


@pytest.fixture(scope="module")
def parsed():
    analyses = {}
    for path in sorted(ROOT.rglob("*.py")):
        analysis = analyse_module(
            source_path=path, relative_path=path.relative_to(ROOT).as_posix(),
            repository_id=REPOSITORY_ID, snapshot_hash=SNAPSHOT_HASH,
        )
        analyses[analysis.module_id] = analysis
    edges, _, warnings = build_edges(analyses)
    graph = to_networkx(build_nodes(analyses), edges)
    units = build_units(graph, {m: a.path for m, a in analyses.items()})
    return {"analyses": analyses, "edges": edges, "warnings": warnings,
            "graph": graph, "units": {u.unit_id: u for u in units}}


def test_every_fixture_module_parses(parsed):
    assert all(a.parsed for a in parsed["analyses"].values())
    assert len(parsed["analyses"]) == 7  # alpha beta gamma leaf shop shop.cart shop.tax


def test_the_scheduling_graph_has_exactly_the_expected_edges(parsed):
    assert set(parsed["graph"].edges()) == EXPECTED_EDGES


def test_both_cycles_are_detected_as_sccs(parsed):
    sccs = [c for c in nx.strongly_connected_components(parsed["graph"]) if len(c) > 1]
    assert sorted(sccs, key=sorted) == EXPECTED_CYCLES
    assert not nx.is_directed_acyclic_graph(parsed["graph"])


def test_each_cycle_becomes_one_unit_flagged_as_a_cycle(parsed):
    units = parsed["units"]
    cycle_units = {uid for uid, u in units.items() if u.is_cycle}
    assert cycle_units == {"unit_alpha+beta", "unit_shop__cart+shop__tax"}

    alpha_beta = units["unit_alpha+beta"]
    assert alpha_beta.module_ids == ["module_alpha", "module_beta"]
    # The patch boundary is both files: a cycle can only be migrated as a whole.
    assert alpha_beta.file_paths == ["alpha.py", "beta.py"]
    assert units["unit_shop__cart+shop__tax"].file_paths == ["shop/cart.py", "shop/tax.py"]


def test_modules_outside_a_cycle_stay_their_own_units(parsed):
    units = parsed["units"]
    for uid in ("unit_gamma", "unit_leaf", "unit_shop"):
        assert units[uid].is_cycle is False
        assert len(units[uid].module_ids) == 1


def test_dependencies_point_at_the_cycle_unit_not_its_members(parsed):
    units = parsed["units"]
    assert units["unit_gamma"].depends_on_unit_ids == ["unit_alpha+beta"]
    assert units["unit_alpha+beta"].depends_on_unit_ids == ["unit_leaf"]
    assert units["unit_shop__cart+shop__tax"].depends_on_unit_ids == []


def test_the_cycle_is_scheduled_after_its_dependency_and_before_its_dependant(parsed):
    units = list(parsed["units"].values())
    statuses = {u.unit_id: "queued" for u in units}

    first = set(eligible_units(units, statuses))
    assert "unit_leaf" in first
    assert "unit_alpha+beta" not in first and "unit_gamma" not in first

    statuses["unit_leaf"] = "passed"
    assert "unit_alpha+beta" in eligible_units(units, statuses)
    assert "unit_gamma" not in eligible_units(units, statuses)

    statuses["unit_alpha+beta"] = "passed"
    assert "unit_gamma" in eligible_units(units, statuses)


def test_relative_imports_resolve_to_the_sibling_module(parsed):
    edge = next(e for e in parsed["edges"] if e.source == "module_shop__cart")
    assert (edge.target, edge.type, edge.resolution) == (
        "module_shop__tax", "from_imports", "confirmed",
    )


def test_a_dynamic_import_is_recorded_but_never_joins_a_cycle(parsed):
    dynamic = [e for e in parsed["edges"] if e.type == "unknown_dynamic"]
    assert [(e.source, e.target, e.resolution) for e in dynamic] == [
        ("module_gamma", "module_beta", "unresolved"),
    ]
    assert any("dynamic import" in w for w in parsed["warnings"])
    # gamma -> beta would not make a cycle anyway, but it must not even be an edge:
    # scheduling uses confirmed static imports only.
    assert not parsed["graph"].has_edge("module_gamma", "module_beta")
