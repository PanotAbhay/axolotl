"""Agent context types and the UnitController Protocol - SHARED_CONTRACTS §8.

Owner: **Dev 1** (`app.agents`). Written by Dev 2 so the orchestrator can construct and
type these today; it is a transcription of §8, not a design. Dev 1 owns and extends it.

`UnitController` is implemented by Dev 2 (`orchestration/controller.py`) and consumed by
Dev 1. It is the only way the model touches the workspace or the verifier: there is no
method here that sets a status, and none that reads held-out case data unexposed.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel

from app.models.contracts import (
    GraphPayload,
    MigrationTarget,
    MigrationUnit,
    PatchAck,
    PatchProposal,
    RepositoryRecord,
)


class PlanContext(BaseModel):
    repository: RepositoryRecord
    graph: GraphPayload
    units: list[MigrationUnit]       # from build_units; Argon may only reorder
    target: MigrationTarget
    module_summaries: dict[str, str]  # module_id -> symbol list / signatures


class UnitSessionContext(BaseModel):
    run_id: str
    repository_id: str
    unit: MigrationUnit
    target: MigrationTarget
    plan_notes: str
    previous_interaction_id: str | None = None
    max_patch_attempts: int           # 3 (1 initial + 2 repairs)
    max_tool_calls: int               # 25


class UnitSessionOutcome(BaseModel):
    ended_because: Literal["verified", "budget_exhausted", "model_gave_up", "error"]
    interaction_ids: list[str] = []
    final_message: str = ""


@runtime_checkable
class UnitController(Protocol):
    """Implemented by Dev 2, consumed by Dev 1."""

    async def submit_patch(self, patch: PatchProposal) -> PatchAck:
        """Fresh workspace from the last accepted revision, validate, apply."""
        ...

    async def run_verification(self) -> dict[str, Any]:
        """Run verify_unit. Returns a model-safe summary.

        The authoritative VerificationResult is persisted by Dev 2; what comes back
        here is deliberately reduced.
        """
        ...

    async def get_counterexamples(self) -> list[dict[str, Any]]:
        """Model-safe: held-out inputs redacted unless already exposed."""
        ...

    async def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """agent_turn / agent_tool_call / agent_tool_result only."""
        ...

    def patch_attempts_remaining(self) -> int: ...

    def is_verified(self) -> bool:
        """True only if the latest persisted VerificationResult says so."""
        ...
