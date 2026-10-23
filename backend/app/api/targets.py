"""Migration targets API - owner: Dev 2. SHARED_CONTRACTS §6.

  GET /migration-targets -> MigrationTarget[]

Only `modern_python3` is supported. The rest are returned with `supported=false` and a
reason so the UI can show them disabled with an explanation rather than hiding them -
asking for one is a 422 UNSUPPORTED_TARGET (T-08). Support wording follows Spec §3.2.
"""

from fastapi import APIRouter

from app.errors import UNSUPPORTED_TARGET, AppError
from app.models.contracts import MigrationTarget

router = APIRouter(tags=["targets"])

MIGRATION_TARGETS: list[MigrationTarget] = [
    MigrationTarget(
        target_id="modern_python3",
        label="Modern Python 3",
        supported=True,
        description=(
            "Legacy-style Python 3 to modern typed Python 3: same public behaviour, "
            "cleaner structure, type hints, dataclasses where safe."
        ),
    ),
    MigrationTarget(
        target_id="fastapi",
        label="Flask to FastAPI",
        supported=False,
        description="Port a Flask-style web layer to FastAPI.",
        unsupported_reason="Stretch goal, not implemented in the MVP.",
    ),
    MigrationTarget(
        target_id="async_python",
        label="Sync to async Python",
        supported=False,
        description="Convert synchronous call paths to async/await.",
        unsupported_reason=(
            "Not in the MVP: changing concurrency changes observable behaviour, so "
            "differential verification would not be meaningful."
        ),
    ),
    MigrationTarget(
        target_id="python_to_typescript",
        label="Python to TypeScript",
        supported=False,
        description="Translate Python modules to TypeScript.",
        unsupported_reason=(
            "Not in the MVP: cross-language migration has no shared runtime for the "
            "differential verifier to execute both sides in."
        ),
    ),
    MigrationTarget(
        target_id="python2_to_3",
        label="Python 2 to Python 3",
        supported=False,
        description="Upgrade a Python 2 codebase to Python 3.",
        unsupported_reason=(
            "Not in the MVP: capturing a baseline needs a Python 2 runtime in the "
            "sandbox, which the runner image does not provide."
        ),
    ),
]

_BY_ID = {target.target_id: target for target in MIGRATION_TARGETS}


@router.get("/migration-targets")
async def list_migration_targets() -> list[MigrationTarget]:
    return MIGRATION_TARGETS


def require_supported_target(target_id: str) -> MigrationTarget:
    """Resolve a target or raise 422 UNSUPPORTED_TARGET (T-08).

    Used by `POST /repositories/{repo_id}/plans`. An unknown id and a known but
    unsupported id both fail the same way, so nothing can start a run on a target the
    verifier cannot handle.
    """
    target = _BY_ID.get(target_id)
    if target is None:
        raise AppError(
            UNSUPPORTED_TARGET,
            f"Unknown migration target {target_id!r}",
            status_code=422,
            details={"target_id": target_id, "supported": ["modern_python3"]},
        )
    if not target.supported:
        raise AppError(
            UNSUPPORTED_TARGET,
            f"Migration target {target_id!r} is not supported",
            status_code=422,
            details={
                "target_id": target_id,
                "reason": target.unsupported_reason,
                "supported": ["modern_python3"],
            },
        )
    return target
