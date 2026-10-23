"""Graph status overlay - owner: Dev 2, consumed by Dev 3. SHARED_CONTRACTS §8.

Dev 3's `GET /repositories/{repo_id}/graph?run_id=` paints each module node with the
status of the migration unit that module belongs to. The mapping lives here because
Dev 2 owns run state; Dev 3 should **call this, never recompute it** from run documents.

Note the key is **module_id, not unit_id**. Graph nodes are modules, and a cyclic unit
covers several of them - every module in an SCC shows that one unit's status.

    from app.orchestration import get_unit_statuses

    statuses = await get_unit_statuses(run_id)
    node.status = statuses.get(node.id, "not_planned")
"""

from __future__ import annotations

from typing import Any

from app.errors import RUN_NOT_FOUND, AppError
from app.models.contracts import UnitStatus
from app.orchestration import store

DEFAULT_STATUS: UnitStatus = "not_planned"


async def get_unit_statuses(run_id: str) -> dict[str, UnitStatus]:
    """module_id -> UnitStatus for one run (SHARED_CONTRACTS §8).

    Modules not covered by the run's plan are simply absent; callers should fall back
    to `not_planned` rather than assuming a missing key is an error.
    """
    run = await store.get_run(run_id)

    statuses: dict[str, UnitStatus] = {}
    for unit_state in run.units:
        for module_id in unit_state.module_ids:
            statuses[module_id] = unit_state.status
    return statuses


async def get_graph_overlay(run_id: str) -> dict[str, dict[str, Any]]:
    """module_id -> {status, unit_id, attempts, accepted_revision}.

    Additive helper beyond §8: `GraphNode` carries `unit_id` as well as `status`, and
    recomputing which unit a module belongs to on Dev 3's side would duplicate the SCC
    grouping. One source of truth is worth the extra function.
    """
    run = await store.get_run(run_id)

    overlay: dict[str, dict[str, Any]] = {}
    for unit_state in run.units:
        for module_id in unit_state.module_ids:
            overlay[module_id] = {
                "status": unit_state.status,
                "unit_id": unit_state.unit_id,
                "attempts": unit_state.attempts,
                "accepted_revision": unit_state.accepted_revision,
            }
    return overlay


async def get_unit_statuses_safe(run_id: str | None) -> dict[str, UnitStatus]:
    """Like `get_unit_statuses`, but an unknown or absent run_id gives {} instead of 404.

    For the graph endpoint, where `run_id` is an optional query parameter: a stale id in
    a bookmarked URL should render an un-overlaid graph, not break the page.
    """
    if not run_id:
        return {}
    try:
        return await get_unit_statuses(run_id)
    except AppError as exc:
        if exc.code == RUN_NOT_FOUND:
            return {}
        raise
