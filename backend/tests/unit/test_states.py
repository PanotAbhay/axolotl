"""State machine unit tests - owner: Dev 2. Spec §6.2.

The central rule being protected: a run must never show `completed` when verification
did not actually pass.
"""

import pytest

from app.orchestration.states import (
    IllegalTransition,
    final_verdict,
    is_terminal_run,
    is_terminal_unit,
    transition_run,
    transition_unit,
)

# --------------------------------------------------------------------------
# run transitions
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("queued", "baselining"),
        ("baselining", "migrating"),
        ("migrating", "verifying"),
        ("verifying", "repairing"),
        ("repairing", "migrating"),
        ("verifying", "migrating"),
        ("verifying", "final_verification"),
        ("final_verification", "completed"),
        ("final_verification", "completed_with_warnings"),
        ("final_verification", "failed"),
    ],
)
def test_legal_run_transitions(current, target):
    assert transition_run("run_1", current, target) == target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("queued", "completed"),            # cannot skip the whole pipeline
        ("queued", "verifying"),
        ("migrating", "completed"),
        ("baselining", "completed_with_warnings"),
        ("verifying", "completed"),         # must go through final_verification
        ("completed", "migrating"),         # terminal
        ("failed", "queued"),
        ("cancelled", "migrating"),
    ],
)
def test_illegal_run_transitions_raise(current, target):
    with pytest.raises(IllegalTransition):
        transition_run("run_1", current, target)


def test_a_run_cannot_reach_completed_without_final_verification():
    """Spec §6.2: never show `completed` when critical verification failed."""
    for state in ["queued", "baselining", "migrating", "verifying", "repairing"]:
        with pytest.raises(IllegalTransition):
            transition_run("run_1", state, "completed")


def test_any_live_run_can_be_cancelled():
    for state in ["queued", "baselining", "migrating", "verifying",
                  "repairing", "final_verification"]:
        assert transition_run("run_1", state, "cancelled") == "cancelled"


def test_a_finished_run_cannot_be_cancelled():
    for state in ["completed", "completed_with_warnings", "failed", "cancelled"]:
        with pytest.raises(IllegalTransition):
            transition_run("run_1", state, "cancelled")


def test_any_live_run_can_fail():
    """A restart marks interrupted runs failed, so this must work from anywhere."""
    for state in ["queued", "baselining", "migrating", "verifying",
                  "repairing", "final_verification"]:
        assert transition_run("run_1", state, "failed") == "failed"


def test_illegal_transition_message_names_what_was_allowed():
    with pytest.raises(IllegalTransition) as caught:
        transition_run("run_7", "queued", "completed")
    message = str(caught.value)
    assert "run_7" in message
    assert "queued -> completed" in message
    assert "baselining" in message


def test_terminal_run_states():
    assert is_terminal_run("completed")
    assert is_terminal_run("cancelled")
    assert not is_terminal_run("migrating")


# --------------------------------------------------------------------------
# unit transitions
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("not_planned", "queued"),
        ("queued", "migrating"),
        ("queued", "skipped"),
        ("migrating", "verifying"),
        ("verifying", "passed"),
        ("verifying", "repairing"),
        ("repairing", "migrating"),
        ("verifying", "blocked"),
    ],
)
def test_legal_unit_transitions(current, target):
    assert transition_unit("unit_pricing", current, target) == target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("queued", "passed"),        # cannot pass without being verified
        ("migrating", "passed"),
        ("not_planned", "migrating"),
        ("passed", "migrating"),     # terminal
        ("blocked", "queued"),
        ("skipped", "migrating"),
    ],
)
def test_illegal_unit_transitions_raise(current, target):
    with pytest.raises(IllegalTransition):
        transition_unit("unit_pricing", current, target)


def test_a_unit_only_passes_out_of_verifying():
    """Only a recorded VerificationResult may move a unit to passed."""
    for status in ["not_planned", "queued", "baselining", "migrating", "repairing"]:
        with pytest.raises(IllegalTransition):
            transition_unit("unit_pricing", status, "passed")


def test_a_skipped_unit_stays_skipped():
    assert is_terminal_unit("skipped")
    with pytest.raises(IllegalTransition):
        transition_unit("unit_orders", "skipped", "queued")


# --------------------------------------------------------------------------
# final verdict
# --------------------------------------------------------------------------

def test_completed_needs_every_unit_passed_and_the_final_gates_green():
    statuses = {"unit_pricing": "passed", "unit_orders": "passed"}
    assert final_verdict(statuses, True) == "completed"


def test_a_blocked_unit_downgrades_to_completed_with_warnings():
    statuses = {"unit_pricing": "passed", "unit_orders": "blocked"}
    assert final_verdict(statuses, True) == "completed_with_warnings"


def test_a_skipped_unit_downgrades_to_completed_with_warnings():
    statuses = {"unit_pricing": "passed", "unit_orders": "skipped"}
    assert final_verdict(statuses, True) == "completed_with_warnings"


def test_an_inconclusive_final_verification_is_never_completed():
    """Runner disabled or timed out: inconclusive counts as not passed."""
    statuses = {"unit_pricing": "passed", "unit_orders": "passed"}
    assert final_verdict(statuses, None) == "completed_with_warnings"


def test_a_failed_final_verification_fails_the_run():
    statuses = {"unit_pricing": "passed", "unit_orders": "passed"}
    assert final_verdict(statuses, False) == "failed"


def test_a_run_with_no_units_is_not_completed():
    assert final_verdict({}, True) == "completed_with_warnings"
