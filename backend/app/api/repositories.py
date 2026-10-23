"""Repositories API - owner: Dev 3. SHARED_CONTRACTS §6.

  GET  /demo-fixtures
  POST /repositories/import                         multipart `file` OR JSON body
  GET  /repositories
  GET  /repositories/{repo_id}
  GET  /repositories/{repo_id}/graph                ?level=module&run_id=
  GET  /repositories/{repo_id}/modules/{module_id}
  GET  /repositories/{repo_id}/symbols/{symbol_id}

Uploaded archives are **static-analysis only**: they import with `executable=False`
and can never be migrated (§0.5). Only the allowlisted demo fixture is executable.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from pydantic import BaseModel

from app import graph as graph_service
from app import ingestion
from app.errors import VALIDATION_ERROR, AppError
from app.models.contracts import GraphPayload, ModuleDetail, RepositoryRecord
from app.persistence.routing import DatabaseAwareRoute

log = logging.getLogger(__name__)
# Atlas going away mid-request is a 503 DATABASE_UNAVAILABLE, never a bare 500 (§9).
router = APIRouter(tags=["repositories"], route_class=DatabaseAwareRoute)

# Module-level singletons: calling File()/Form() inline in a default is a ruff B008.
_OPTIONAL_FILE = File(None)
_OPTIONAL_FORM = Form(None)


class ImportFixtureRequest(BaseModel):
    demo_fixture_id: str
    name: str | None = None


@router.get("/demo-fixtures")
async def list_demo_fixtures() -> list[dict[str, str]]:
    return await ingestion.list_demo_fixtures()


@router.post("/repositories/import")
async def import_repository(
    request: Request,
    file: UploadFile | None = _OPTIONAL_FILE,
    demo_fixture_id: str | None = _OPTIONAL_FORM,
    name: str | None = _OPTIONAL_FORM,
) -> RepositoryRecord:
    """Import a ZIP upload or an allowlisted demo fixture.

    Accepts either a multipart upload or a JSON body, because §6 specifies both and
    the frontend uses the JSON form for the fixture.
    """
    if file is None and demo_fixture_id is None:
        demo_fixture_id, name = await _fixture_from_json(request)

    if file is not None:
        # Spool to disk: the archive is untrusted and may be large, and the safety
        # checks work on a real file rather than a stream we have already buffered.
        with tempfile.TemporaryDirectory(prefix="axolotl-upload-") as tmp:
            upload = Path(tmp) / (Path(file.filename or "upload.zip").name)
            upload.write_bytes(await file.read())
            return await ingestion.import_repository(
                zip_path=upload, name=name or upload.stem
            )

    return await ingestion.import_repository(
        demo_fixture_id=demo_fixture_id, name=name
    )


async def _fixture_from_json(request: Request) -> tuple[str, str | None]:
    try:
        body: Any = await request.json()
    except Exception as exc:  # noqa: BLE001 - a malformed body is a 422, not a 500
        raise AppError(
            VALIDATION_ERROR,
            "Send a multipart `file` upload or a JSON body with demo_fixture_id",
            status_code=422,
        ) from exc

    parsed = ImportFixtureRequest.model_validate(body)
    return parsed.demo_fixture_id, parsed.name


@router.get("/repositories")
async def list_repositories() -> list[RepositoryRecord]:
    return await ingestion.list_repositories()


@router.get("/repositories/{repo_id}")
async def get_repository(repo_id: str) -> RepositoryRecord:
    return await ingestion.get_repository(repo_id)


@router.get("/repositories/{repo_id}/graph")
async def get_graph(
    repo_id: str,
    level: str = Query("module"),
    run_id: str | None = Query(None),
) -> GraphPayload:
    if level != "module":
        raise AppError(
            VALIDATION_ERROR,
            f"Only module-level graphs are supported, got {level!r}",
            status_code=422,
            details={"supported": ["module"]},
        )
    return await graph_service.get_graph(repo_id, run_id)


@router.get("/repositories/{repo_id}/modules/{module_id}")
async def get_module_detail(repo_id: str, module_id: str) -> ModuleDetail:
    return await graph_service.get_module_detail(repo_id, module_id)


@router.get("/repositories/{repo_id}/symbols/{symbol_id}")
async def get_symbol(repo_id: str, symbol_id: str) -> dict[str, Any]:
    """`SymbolRecord` plus the source it spans (§6).

    `warnings` is additive (§11): it says when the source cannot be shown, e.g. the
    snapshot is not on this machine, so an empty `source` is never left unexplained.
    """
    symbol, source, warnings = await graph_service.get_symbol_detail(repo_id, symbol_id)
    return {**symbol.model_dump(), "source": source, "warnings": warnings}


@router.get("/repositories/{repo_id}/runtime")
async def get_runtime(repo_id: str) -> dict:
    """Declared source requirements only; not a claim of runtime compatibility."""
    from app.ingestion.runtime import inspect_runtime

    await ingestion.get_repository(repo_id)
    return inspect_runtime(ingestion.snapshot_path(repo_id))
