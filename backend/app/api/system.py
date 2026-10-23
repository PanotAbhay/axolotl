"""System API - owner: Dev 2. Aggregates health from every owner's package.

SHARED_CONTRACTS §6:
  GET /system/status -> {mongodb, search_indexes:{keyword,vector},
                         runner:{mode,available}, gemini:{model,reachable}}

The Mongo check is a real `ping` against Atlas. The others call into their owners'
packages; those report honestly as unavailable until wired, and are never faked.
"""

from typing import Any

from fastapi import APIRouter

from app.agents.health import gemini_status
from app.config import get_settings
from app.persistence import db
from app.persistence.search_health import search_index_status
from app.sandbox import runner_status

router = APIRouter(tags=["system"])


@router.get("/system/status")
async def get_system_status() -> dict[str, Any]:
    settings = get_settings()

    mongo_ok, mongo_error = await db.ping()
    mongodb = "ok" if mongo_ok else "unavailable"

    indexes = await search_index_status(mongo_ok)
    runner = await runner_status()
    gemini = await gemini_status()

    status: dict[str, Any] = {
        "mongodb": mongodb,
        "search_indexes": indexes,
        "runner": {"mode": runner["mode"], "available": runner["available"]},
        "gemini": {"model": settings.gemini_model, "reachable": gemini["reachable"]},
    }

    # Non-contract diagnostics, additive and safe for the UI to ignore.
    details: dict[str, Any] = {}
    if mongo_error:
        details["mongodb"] = mongo_error
    else:
        version = await db.server_version()
        if version:
            details["mongodb_version"] = version
    if runner.get("detail"):
        details["runner"] = runner["detail"]
    if gemini.get("detail"):
        details["gemini"] = gemini["detail"]
    if details:
        status["details"] = details

    return status
