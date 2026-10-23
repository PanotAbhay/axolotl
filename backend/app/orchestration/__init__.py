"""Orchestration - owner: Dev 2. State machine, scheduler, events, controller, worker.

This module re-exports the SHARED_CONTRACTS §8 surface other devs consume, so nobody
has to know which file a function lives in:

    from app.orchestration import build_units, eligible_units, impacted_units
    from app.orchestration import append_event, list_events, get_unit_statuses
    from app.orchestration import create_plan, start_run

Dev 1 additionally uses `UnitController` from `app.agents.contexts`; Dev 2 implements
it as `UnitControllerImpl` here.
"""

from app.orchestration.controller import UnitControllerImpl
from app.orchestration.events import append_event, list_events, redact
from app.orchestration.overlay import (
    get_graph_overlay,
    get_unit_statuses,
    get_unit_statuses_safe,
)
from app.orchestration.plans import approve_plan, create_plan
from app.orchestration.scheduler import (
    build_units,
    eligible_units,
    impacted_units,
    units_to_skip,
)
from app.orchestration.states import (
    IllegalTransition,
    final_verdict,
    transition_run,
    transition_unit,
)
from app.orchestration.worker import cancel_run, mark_interrupted_runs, start_run

__all__ = [
    "IllegalTransition",
    "UnitControllerImpl",
    "append_event",
    "approve_plan",
    "build_units",
    "cancel_run",
    "create_plan",
    "eligible_units",
    "final_verdict",
    "get_graph_overlay",
    "get_unit_statuses",
    "get_unit_statuses_safe",
    "impacted_units",
    "list_events",
    "mark_interrupted_runs",
    "redact",
    "start_run",
    "transition_run",
    "transition_unit",
    "units_to_skip",
]
