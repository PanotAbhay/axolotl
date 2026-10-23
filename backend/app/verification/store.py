"""Verification persistence - owner: Dev 4. SHARED_CONTRACTS §9.

Collections: `verification_results`, `counterexamples`, and `baseline_outcomes`.

`baseline_outcomes` is additive - §9 does not list it, but the baseline has to be
recorded somewhere for the differential to compare against, and keeping it in its own
collection means a run's oracle is queryable and auditable rather than held in
memory where a restart would lose it.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.contracts import CaseOutcome, Counterexample, VerificationResult
from app.persistence import db

log = logging.getLogger(__name__)

VERIFICATIONS = "verification_results"
COUNTEREXAMPLES = "counterexamples"
BASELINE_OUTCOMES = "baseline_outcomes"


async def ensure_indexes() -> None:
    database = await db.get_db()
    await database[VERIFICATIONS].create_index(
        "verification_id", unique=True, name="verification_id_unique"
    )
    await database[VERIFICATIONS].create_index(
        [("run_id", 1), ("unit_id", 1)], name="verification_run_unit"
    )
    await database[COUNTEREXAMPLES].create_index(
        "counterexample_id", unique=True, name="counterexample_id_unique"
    )
    await database[COUNTEREXAMPLES].create_index(
        [("run_id", 1), ("unit_id", 1), ("status", 1)], name="counterexample_run_unit"
    )
    await database[BASELINE_OUTCOMES].create_index(
        [("run_id", 1), ("case_id", 1)], unique=True, name="baseline_run_case"
    )


# --------------------------------------------------------------------------
# baseline outcomes - the oracle
# --------------------------------------------------------------------------

async def save_baseline_outcomes(run_id: str, outcomes: list[CaseOutcome]) -> int:
    database = await db.get_db()
    await database[BASELINE_OUTCOMES].delete_many({"run_id": run_id})
    if outcomes:
        await database[BASELINE_OUTCOMES].insert_many(
            [{"run_id": run_id, "case_id": o.case_id, **o.model_dump()}
             for o in outcomes]
        )
    return len(outcomes)


async def get_baseline_outcomes(run_id: str) -> dict[str, CaseOutcome]:
    """case_id -> the outcome recorded against the immutable baseline."""
    database = await db.get_db()
    cursor = database[BASELINE_OUTCOMES].find({"run_id": run_id}, {"_id": 0, "run_id": 0})
    return {
        document["case_id"]: CaseOutcome(**document) async for document in cursor
    }


# --------------------------------------------------------------------------
# verification results
# --------------------------------------------------------------------------

async def save_verification(result: VerificationResult) -> VerificationResult:
    database = await db.get_db()
    await database[VERIFICATIONS].replace_one(
        {"verification_id": result.verification_id}, result.model_dump(), upsert=True
    )
    return result


async def list_verifications(
    run_id: str, unit_id: str | None = None
) -> list[VerificationResult]:
    database = await db.get_db()
    query: dict[str, Any] = {"run_id": run_id}
    if unit_id is not None:
        query["unit_id"] = unit_id
    cursor = database[VERIFICATIONS].find(query, {"_id": 0}).sort("started_at", 1)
    return [VerificationResult(**document) async for document in cursor]


# --------------------------------------------------------------------------
# counterexamples
# --------------------------------------------------------------------------

async def save_counterexamples(items: list[Counterexample]) -> int:
    if not items:
        return 0
    database = await db.get_db()
    for item in items:
        await database[COUNTEREXAMPLES].replace_one(
            {"counterexample_id": item.counterexample_id},
            item.model_dump(), upsert=True,
        )
    return len(items)


async def list_counterexamples(
    run_id: str, unit_id: str | None = None
) -> list[Counterexample]:
    database = await db.get_db()
    query: dict[str, Any] = {"run_id": run_id}
    if unit_id is not None:
        query["unit_id"] = unit_id
    cursor = database[COUNTEREXAMPLES].find(query, {"_id": 0}).sort("case_id", 1)
    return [Counterexample(**document) async for document in cursor]


async def resolve_counterexamples(run_id: str, unit_id: str, verification_id: str) -> int:
    """Mark a unit's open counterexamples resolved once it verifies."""
    database = await db.get_db()
    result = await database[COUNTEREXAMPLES].update_many(
        {"run_id": run_id, "unit_id": unit_id, "status": "open"},
        {"$set": {"status": "resolved",
                  "resolved_by_verification_id": verification_id}},
    )
    return int(result.modified_count)


async def mark_case_exposed(run_id: str, case_id: str) -> int:
    database = await db.get_db()
    result = await database[COUNTEREXAMPLES].update_many(
        {"run_id": run_id, "case_id": case_id},
        {"$set": {"exposed_to_model": True}},
    )
    return int(result.modified_count)
