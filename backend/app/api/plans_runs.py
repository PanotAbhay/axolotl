"""Plans & runs API - owner: Dev 2. SHARED_CONTRACTS §6.

The frontend polls GET /runs/{id} and /runs/{id}/events?after_sequence=N every 1.5 s
while a run is non-terminal.

Held-out case inputs are redacted on the unit endpoint unless `exposed_to_model`:
the API is the boundary that protects the held-out suite, not the sandbox.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.errors import ARTEFACT_NOT_FOUND, REPORT_NOT_READY, AppError
from app.models.contracts import (
    MigrationPlan,
    RunEvent,
    RunReport,
    RunSummary,
)
from app.orchestration import events, plans, ports, store, worker
from app.persistence.routing import DatabaseAwareRoute
from app.reports.builder import get_report

# `route_class` turns a driver failure into 503 DATABASE_UNAVAILABLE instead of a bare
# 500 (Dev 3's DatabaseAwareRoute). Deliberately per-router rather than a global
# handler in errors.py: `/system/status` must answer 200 while *reporting* mongodb as
# unavailable, and a global handler would turn that status report into a 503.
router = APIRouter(tags=["plans", "runs"], route_class=DatabaseAwareRoute)


class CreatePlanRequest(BaseModel):
    target_id: str


class ApprovePlanRequest(BaseModel):
    approved: bool


# --------------------------------------------------------------------------
# plans
# --------------------------------------------------------------------------

@router.post("/repositories/{repo_id}/plans")
async def create_plan(repo_id: str, body: CreatePlanRequest) -> MigrationPlan:
    """422 UNSUPPORTED_TARGET (T-08), 409 REPOSITORY_NOT_EXECUTABLE."""
    return await plans.create_plan(repo_id, body.target_id)


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str) -> MigrationPlan:
    return await store.get_plan(plan_id)


@router.post("/plans/{plan_id}/approve")
async def approve_plan(plan_id: str, body: ApprovePlanRequest) -> MigrationPlan:
    return await plans.approve_plan(plan_id, body.approved)


# --------------------------------------------------------------------------
# runs
# --------------------------------------------------------------------------

@router.post("/plans/{plan_id}/runs")
async def start_run(plan_id: str) -> RunSummary:
    """409 PLAN_NOT_APPROVED if the plan has not been approved."""
    return await worker.start_run(plan_id)


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> RunSummary:
    return await store.get_run(run_id)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> RunSummary:
    return await worker.cancel_run(run_id)


@router.get("/runs/{run_id}/events")
async def list_run_events(
    run_id: str,
    after_sequence: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
) -> list[RunEvent]:
    await store.get_run(run_id)  # 404 RUN_NOT_FOUND for an unknown run
    return await events.list_events(run_id, after_sequence, limit)


@router.get("/runs/{run_id}/units/{unit_id}")
async def get_run_unit(run_id: str, unit_id: str) -> dict[str, Any]:
    """Verifications and counterexamples for one unit.

    `for_model=False`: this is the human view, so exposed held-out cases are labelled
    rather than hidden. Dev 4 still redacts unexposed held-out values.
    """
    run = await store.get_run(run_id)
    unit = next((s for s in run.units if s.unit_id == unit_id), None)
    if unit is None:
        raise AppError(
            "UNIT_NOT_FOUND", f"No unit {unit_id!r} in run {run_id}",
            status_code=404, details={"run_id": run_id, "unit_id": unit_id},
        )

    try:
        counterexamples = await ports.get_counterexamples(
            run_id, unit_id, for_model=False
        )
    except ports.IntegrationUnavailable:
        counterexamples = []

    return {
        "unit": unit.model_dump(),
        "verifications": [],  # Dev 4 owns verification_results; read when it lands
        "counterexamples": [
            _redact_held_out(c if isinstance(c, dict) else c.model_dump())
            for c in counterexamples
        ],
    }


REDACTED_HELD_OUT = "held-out case - redacted"


def _redact_held_out(counterexample: dict[str, Any]) -> dict[str, Any]:
    """Strip held-out inputs and values unless the case was exposed during repair.

    `for_model=False` asks Dev 4 for the full record, which is right for the human
    view: a reviewer may see that a held-out case failed, and may see an exposed
    one in full. They must not see the inputs or expected values of a held-out case
    that is still sealed - the UI is a read path like any other, and leaking there
    would quietly destroy the independence of the held-out suite.
    """
    if counterexample.get("visibility") != "held_out":
        return counterexample
    if counterexample.get("exposed_to_model"):
        return counterexample

    redacted = dict(counterexample)
    for field in ("args", "kwargs", "old", "new", "function"):
        if field in redacted:
            redacted[field] = REDACTED_HELD_OUT
    redacted["redacted"] = True
    return redacted


@router.get("/runs/{run_id}/diff")
async def get_run_diff(run_id: str, unit_id: str | None = None) -> dict[str, Any]:
    """T-16: the diff shown must be the diff of the verified accepted revision."""
    run = await store.get_run(run_id)

    # The whole journal: with a 1000-event ceiling a long run would hand us an
    # intermediate revision and we would serve it as the verified one (T-16).
    accepted = [
        e for e in await events.list_all_events(run_id)
        if e.event_type == "snapshot_accepted"
    ]
    if not accepted:
        return {"base_revision": "rev_baseline", "revision": None, "files": []}

    revision = accepted[-1].payload.get("revision")
    paths = None
    if unit_id:
        plan = await store.get_plan(run.plan_id)
        unit = next((u for u in plan.units if u.unit_id == unit_id), None)
        if unit is None:
            # Silently returning the whole-run diff would answer a different
            # question than the one asked.
            raise AppError(
                "UNIT_NOT_FOUND",
                f"No unit {unit_id!r} in the plan for run {run_id}",
                status_code=404,
                details={"run_id": run_id, "unit_id": unit_id},
            )
        paths = unit.file_paths

    try:
        files = await ports.diff(run_id, "rev_baseline", revision, paths)
    except ports.IntegrationUnavailable as exc:
        raise AppError(
            "INTEGRATION_UNAVAILABLE", str(exc), status_code=503,
            details={"owner": exc.owner},
        ) from exc

    return {"base_revision": "rev_baseline", "revision": revision, "files": files}


@router.get("/runs/{run_id}/report")
async def get_run_report(run_id: str) -> RunReport:
    """404 until the run has finished and a report has been generated."""
    await store.get_run(run_id)
    report = await get_report(run_id)
    if report is None:
        raise AppError(
            REPORT_NOT_READY,
            f"No report for {run_id} yet; it is generated when the run finishes",
            status_code=404,
            details={"run_id": run_id},
        )
    return report


# --------------------------------------------------------------------------
# artefacts
# --------------------------------------------------------------------------

@router.get("/runs/{run_id}/artefacts")
async def list_run_artefacts(run_id: str) -> list[dict[str, Any]]:
    await store.get_run(run_id)
    return [
        {
            "artefact_id": a["artefact_id"],
            "kind": a["kind"],
            "sha256": a["sha256"],
            "download_url": f"/api/v1/artefacts/{a['artefact_id']}/download",
        }
        for a in await store.list_artefacts(run_id)
    ]


@router.get("/artefacts/{artefact_id}/download")
async def download_artefact(artefact_id: str) -> FileResponse:
    artefact = await store.get_artefact(artefact_id)
    path = Path(artefact["path"])
    if not path.is_file():
        raise AppError(
            ARTEFACT_NOT_FOUND,
            f"Artefact {artefact_id} is recorded but its file is missing",
            status_code=404,
            details={"artefact_id": artefact_id},
        )
    return FileResponse(path, filename=path.name)
