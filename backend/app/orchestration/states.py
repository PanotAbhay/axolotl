"""Run and unit state machines - owner: Dev 2. Spec §6.2.

Every state change goes through `transition_run` or `transition_unit`. They raise on
an illegal move rather than letting a run drift into a state nobody designed.

**Reconciliation (SHARED_CONTRACTS §11 needed).** Spec §6.2 is one combined diagram
containing `parsing`, `planning` and `awaiting_approval`, and has no transition into
or out of `cancelled`. SHARED_CONTRACTS §4 `RunState` has none of those three and does
have `cancelled`. SHARED_CONTRACTS §0 says it wins on names and shapes, so the tables
below are built over the `RunState` / `UnitStatus` literals, with §6.2's shape mapped
onto them:

  - `parsing` / `planning` / `awaiting_approval` happen before a run exists. A run is
    created only once a plan is approved, so it starts at `queued`.
  - `cancelled` is reachable from any non-terminal run state (the brief requires a
    cancel flag checked between steps).
  - Unit `skipped` implements T-13 and `not_planned` is the pre-run default; neither
    appears in §6.2 but both are in `UnitStatus`.
"""

from __future__ import annotations

from app.models.contracts import RunState, UnitStatus

# --------------------------------------------------------------------------
# run states
# --------------------------------------------------------------------------

TERMINAL_RUN_STATES: frozenset[str] = frozenset(
    {"completed", "completed_with_warnings", "failed", "cancelled"}
)

_RUN_TRANSITIONS: dict[str, frozenset[str]] = {
    "queued": frozenset({"baselining", "failed"}),
    "baselining": frozenset({"migrating", "final_verification", "failed"}),
    # migrating -> final_verification covers a plan whose every unit was skipped.
    "migrating": frozenset({"verifying", "final_verification", "failed"}),
    "verifying": frozenset({"migrating", "repairing", "final_verification", "failed"}),
    "repairing": frozenset({"migrating", "verifying", "final_verification", "failed"}),
    "final_verification": frozenset(
        {"completed", "completed_with_warnings", "failed"}
    ),
    "completed": frozenset(),
    "completed_with_warnings": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}

# --------------------------------------------------------------------------
# unit states
# --------------------------------------------------------------------------

TERMINAL_UNIT_STATUSES: frozenset[str] = frozenset(
    {"passed", "blocked", "failed", "skipped"}
)

# `skipped` is reachable from every non-terminal unit state. From `queued` it means
# T-13 - a prerequisite was blocked, so this was never attempted. From the in-flight
# states it means the run was cancelled and this unit was abandoned part-way.
# `UnitStatus` has no "cancelled" and §6.2 has no cancellation at all, so `skipped`
# carries both; the `unit_state_changed` event records which.
_UNIT_TRANSITIONS: dict[str, frozenset[str]] = {
    "not_planned": frozenset({"queued"}),
    "queued": frozenset({"baselining", "migrating", "skipped"}),
    "baselining": frozenset({"queued", "migrating", "blocked", "failed", "skipped"}),
    "migrating": frozenset({"verifying", "blocked", "failed", "skipped"}),
    "verifying": frozenset({"passed", "repairing", "blocked", "failed", "skipped"}),
    # The brief sets `repairing` in submit_patch on attempt >= 2, so a unit goes
    # verifying -> repairing -> migrating for the next attempt.
    "repairing": frozenset({"migrating", "verifying", "blocked", "failed", "skipped"}),
    "passed": frozenset(),
    "blocked": frozenset(),
    "failed": frozenset(),
    "skipped": frozenset(),
}


class IllegalTransition(Exception):
    """Raised when something tries to move a run or unit somewhere it cannot go."""

    def __init__(self, kind: str, identifier: str, current: str, target: str) -> None:
        allowed = sorted(
            (_RUN_TRANSITIONS if kind == "run" else _UNIT_TRANSITIONS).get(
                current, frozenset()
            )
        )
        super().__init__(
            f"illegal {kind} transition for {identifier}: {current} -> {target} "
            f"(allowed from {current}: {', '.join(allowed) or 'none'})"
        )
        self.kind = kind
        self.identifier = identifier
        self.current = current
        self.target = target


def can_transition_run(current: RunState, target: RunState) -> bool:
    return target in _RUN_TRANSITIONS.get(current, frozenset())


def can_transition_unit(current: UnitStatus, target: UnitStatus) -> bool:
    return target in _UNIT_TRANSITIONS.get(current, frozenset())


def transition_run(run_id: str, current: RunState, target: RunState) -> RunState:
    """Validate a run state change. Returns the new state or raises.

    `cancelled` is allowed from any non-terminal state; the worker checks a cancel
    flag between steps.
    """
    if target == "cancelled":
        if current in TERMINAL_RUN_STATES:
            raise IllegalTransition("run", run_id, current, target)
        return target
    if not can_transition_run(current, target):
        raise IllegalTransition("run", run_id, current, target)
    return target


def transition_unit(unit_id: str, current: UnitStatus, target: UnitStatus) -> UnitStatus:
    """Validate a unit status change. Returns the new status or raises."""
    if not can_transition_unit(current, target):
        raise IllegalTransition("unit", unit_id, current, target)
    return target


def is_terminal_run(state: RunState) -> bool:
    return state in TERMINAL_RUN_STATES


def is_terminal_unit(status: UnitStatus) -> bool:
    return status in TERMINAL_UNIT_STATUSES


def final_verdict(
    unit_statuses: dict[str, UnitStatus], final_gates_passed: bool | None
) -> RunState:
    """Spec §6.6 / §7.6: decide a run's terminal state from recorded evidence only.

    `final_gates_passed` is None when the final verification was inconclusive - for
    example the runner was disabled, which never counts as a pass.

    `completed` requires every unit passed AND the final gates passed. Anything less
    is `completed_with_warnings`. Never show `completed` when verification failed.
    """
    if final_gates_passed is False:
        return "failed"

    every_unit_passed = bool(unit_statuses) and all(
        status == "passed" for status in unit_statuses.values()
    )

    if every_unit_passed and final_gates_passed is True:
        return "completed"
    return "completed_with_warnings"
