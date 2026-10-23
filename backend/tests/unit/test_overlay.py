"""Graph overlay tests - owner: Dev 2, consumed by Dev 3.

The thing worth pinning: the overlay is keyed by **module_id**, not unit_id, and a
cyclic unit paints every module it covers. Dev 3's graph nodes are modules, so getting
this wrong would silently mis-colour an SCC.
"""

import pytest

from app.errors import RUN_NOT_FOUND, AppError
from app.models.contracts import RunSummary, UnitRunState
from app.orchestration import overlay as overlay_module
from app.orchestration import store as store_module
from app.orchestration.overlay import (
    get_graph_overlay,
    get_unit_statuses,
    get_unit_statuses_safe,
)


def make_run(units: list[UnitRunState]) -> RunSummary:
    now = store_module.utcnow()
    return RunSummary(
        run_id="run_000000000001",
        plan_id="plan_000000000001",
        repository_id="repo_000000000001",
        state="migrating",
        current_unit=None,
        units=units,
        units_total=len(units),
        units_verified=0,
        units_blocked=0,
        tests_passed=0,
        tests_failed=0,
        tests_inconclusive=0,
        last_event_sequence=1,
        model="gemini-4-argon",
        runner_mode="trusted_docker",
        created_at=now,
        updated_at=now,
    )


UNITS = [
    UnitRunState(unit_id="unit_pricing", module_ids=["module_pricing"], status="passed",
                 attempts=2, accepted_revision="rev_aaaaaaaaaaaa"),
    UnitRunState(unit_id="unit_orders", module_ids=["module_orders"], status="migrating"),
    # a cycle: two modules, one unit
    UnitRunState(unit_id="unit_a+b", module_ids=["module_a", "module_b"],
                 status="blocked"),
]


@pytest.fixture
def run(monkeypatch):
    async def get_run(run_id):
        if run_id != "run_000000000001":
            raise AppError(RUN_NOT_FOUND, f"No run {run_id!r}", status_code=404)
        return make_run(UNITS)

    monkeypatch.setattr(store_module, "get_run", get_run)
    monkeypatch.setattr(overlay_module.store, "get_run", get_run)


async def test_statuses_are_keyed_by_module_not_unit(run):
    statuses = await get_unit_statuses("run_000000000001")
    assert statuses["module_pricing"] == "passed"
    assert statuses["module_orders"] == "migrating"
    assert "unit_pricing" not in statuses


async def test_every_module_in_a_cycle_gets_the_unit_s_status(run):
    """One blocked SCC must colour both its modules, not just the first."""
    statuses = await get_unit_statuses("run_000000000001")
    assert statuses["module_a"] == "blocked"
    assert statuses["module_b"] == "blocked"


async def test_modules_outside_the_plan_are_absent(run):
    statuses = await get_unit_statuses("run_000000000001")
    assert "module_not_in_plan" not in statuses
    assert statuses.get("module_not_in_plan", "not_planned") == "not_planned"


async def test_overlay_carries_the_unit_id_too(run):
    overlay = await get_graph_overlay("run_000000000001")
    assert overlay["module_a"]["unit_id"] == "unit_a+b"
    assert overlay["module_b"]["unit_id"] == "unit_a+b"
    assert overlay["module_pricing"]["unit_id"] == "unit_pricing"


async def test_overlay_carries_attempts_and_accepted_revision(run):
    overlay = await get_graph_overlay("run_000000000001")
    assert overlay["module_pricing"]["attempts"] == 2
    assert overlay["module_pricing"]["accepted_revision"] == "rev_aaaaaaaaaaaa"
    assert overlay["module_orders"]["accepted_revision"] is None


async def test_an_unknown_run_is_a_404(run):
    with pytest.raises(AppError) as caught:
        await get_unit_statuses("run_doesnotexist")
    assert caught.value.status_code == 404


async def test_the_safe_variant_renders_an_unoverlaid_graph_instead_of_breaking(run):
    """A stale run_id in a bookmarked URL should not break Dev 3's graph page."""
    assert await get_unit_statuses_safe("run_doesnotexist") == {}
    assert await get_unit_statuses_safe(None) == {}
    assert await get_unit_statuses_safe("") == {}


async def test_the_safe_variant_still_returns_a_real_overlay(run):
    assert (await get_unit_statuses_safe("run_000000000001"))["module_pricing"] == "passed"


async def test_the_safe_variant_does_not_swallow_a_database_outage(monkeypatch):
    """503 must still surface - only RUN_NOT_FOUND is softened."""
    from app.errors import database_unavailable

    async def get_run(run_id):
        raise database_unavailable()

    monkeypatch.setattr(overlay_module.store, "get_run", get_run)

    with pytest.raises(AppError) as caught:
        await get_unit_statuses_safe("run_000000000001")
    assert caught.value.status_code == 503
