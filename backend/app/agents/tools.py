"""Validated local tools; repository identity is bound by the session, never the model."""

from __future__ import annotations

import importlib
import json
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.errors import AppError
from app.models.contracts import PatchProposal
from app.orchestration.events import redact


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Empty(Args):
    pass


class ModuleArgs(Args):
    module_id: str


class SymbolArgs(Args):
    symbol_id: str | None = None
    qualified_name: str | None = None


class SearchArgs(Args):
    query: str = Field(min_length=1, max_length=2000)
    mode: Literal["keyword", "vector", "hybrid"] = "hybrid"


class FileArgs(Args):
    path: str
    new_content: str


class PatchArgs(Args):
    files: list[FileArgs] = Field(min_length=1)
    summary: str
    rationale: str


class FinishArgs(Args):
    reason: str


TOOL_MODELS = {
    "get_repository_overview": (Empty, "Read repository metadata and graph counts."),
    "get_dependency_graph": (Empty, "Read compact dependency edges; A depends on B."),
    "get_module_source": (ModuleArgs, "Read original module source in this repository."),
    "get_symbol": (SymbolArgs, "Read a symbol by id or qualified name."),
    "search_repository": (SearchArgs, "Search this repository; at most eight hits."),
    "get_behaviour_cases": (Empty, "Read only visible behaviour cases for this unit."),
    "propose_patch": (PatchArgs, "Submit full-file replacements within the unit allowlist."),
    "run_verification": (Empty, "Independently verify the last accepted patch."),
    "get_counterexamples": (Empty, "Read model-safe failures from the verifier."),
    "finish_unit": (FinishArgs, "Stop with a reason; this never marks a unit verified."),
}


def schema(name, model, description):
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": model.model_json_schema(),
    }


TOOL_SCHEMAS = [schema(name, *definition) for name, definition in TOOL_MODELS.items()]


def json_value(value):
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    if isinstance(value, dict):
        return {k: json_value(v) for k, v in value.items()}
    return value


def safe_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return (
        bool(parts)
        and not PurePosixPath(path).is_absolute()
        and not any(p in ("..", "challenge_cases") or ":" in p for p in parts)
        and "\\" not in path
        and "\x00" not in path
    )


class ToolDispatcher:
    def __init__(self, ctx, controller):
        self.ctx, self.controller = ctx, controller
        self.finished = False
        self.reason = ""
        self.pending_patch = False
        self.repair = False
        self.patch_calls = 0

    async def service(self, module, name, *args, **kwargs):
        function = getattr(importlib.import_module(module), name, None)
        if function is None:
            return {"error": "tool_unavailable", "tool": name}
        try:
            return json_value(await function(*args, **kwargs))
        except AppError as exc:
            return {"error": exc.code, "message": redact(str(exc))}

    async def execute(self, name, raw):
        if name not in TOOL_MODELS:
            return {"error": "unknown_tool"}
        try:
            if isinstance(raw, str):
                raw = json.loads(raw)
            args = TOOL_MODELS[name][0].model_validate(raw)
        except (ValidationError, ValueError, TypeError):
            return {
                "error": "invalid_arguments",
                "tool": name,
                "message": "Use the declared schema; retry once with valid arguments.",
            }
        repo = self.ctx.repository_id
        if name == "finish_unit":
            if self.pending_patch:
                return {"error": "verification_required"}
            self.finished, self.reason = True, args.reason
            return {"finished": True, "verified": self.controller.is_verified()}
        if name == "propose_patch":
            if (
                self.patch_calls >= self.ctx.max_patch_attempts
                or self.controller.patch_attempts_remaining() <= 0
            ):
                return {"error": "patch_budget_exhausted"}
            self.patch_calls += 1
            paths = [f.path for f in args.files]
            if (
                len(paths) != len(set(paths))
                or any(
                    not safe_path(p)
                    or p not in self.ctx.unit.file_paths
                    or "tests" in PurePosixPath(p).parts
                    or PurePosixPath(p).name.startswith("test_")
                    or PurePosixPath(p).name == "conftest.py"
                    for p in paths
                )
                or any(len(f.new_content.encode("utf-8")) > 65536 for f in args.files)
            ):
                return {
                    "error": "patch_rejected",
                    "message": "Invalid path, duplicate or file >64KB",
                }
            if self.pending_patch:
                return {"error": "verification_required"}
            proposal = PatchProposal(unit_id=self.ctx.unit.unit_id, **args.model_dump())
            ack = await self.controller.submit_patch(proposal)
            self.pending_patch = ack.accepted
            return json_value(ack)
        if name == "run_verification":
            if not self.pending_patch:
                return {"error": "no_pending_patch"}
            result = await self.controller.run_verification()
            self.pending_patch = False
            self.repair = not self.controller.is_verified()
            return json_value(result)
        if name == "get_counterexamples":
            return await self.controller.get_counterexamples()
        if name == "get_behaviour_cases":
            cases = await self.service(
                "app.verification",
                "load_cases",
                repo,
                self.ctx.unit.unit_id,
                include_held_out=False,
            )
            if isinstance(cases, dict):
                return cases
            return {
                "visible_cases": [c for c in cases if c.get("visibility") == "visible"],
                "held_out_count": None,
                "note": "Held-out inputs excluded; total count not provided by this interface.",
            }
        if name == "get_repository_overview":
            return await self.service("app.ingestion", "get_repository", repo)
        if name == "get_dependency_graph":
            graph = await self.service("app.graph", "get_graph", repo)
            if "error" in graph:
                return graph
            return {
                "nodes": [{k: n[k] for k in ("id", "path", "kind")} for n in graph["nodes"]],
                "edges": [
                    {k: e[k] for k in ("source", "target", "type", "resolution")}
                    for e in graph["edges"]
                ],
            }
        if name == "get_module_source":
            detail = await self.service("app.graph", "get_module_detail", repo, args.module_id)
            if "error" not in detail and not safe_path(detail["path"]):
                return {"error": "protected_path"}
            return detail
        if name == "get_symbol":
            if bool(args.symbol_id) == bool(args.qualified_name):
                return {"error": "supply_exactly_one_symbol_identifier"}
            symbol_id = args.symbol_id
            if not symbol_id:
                record = await self.service("app.graph", "find_symbol", repo, args.qualified_name)
                if not record or "error" in record:
                    return record or {"error": "symbol_not_found"}
                symbol_id = record["symbol_id"]
            result = await self.service("app.graph", "get_symbol", repo, symbol_id)
            if isinstance(result, list) and not safe_path(result[0]["path"]):
                return {"error": "protected_path"}
            return result
        if name == "search_repository":
            hits = await self.service(
                "app.search", "search_repository", repo, args.query, mode=args.mode, limit=8
            )
            if isinstance(hits, dict):
                if "error" in hits:
                    return hits
                return {
                    **hits,
                    "hits": [h for h in hits.get("hits", []) if safe_path(h["path"])][:8],
                }
            return [h for h in hits if safe_path(h["path"])][:8]
        return {"error": "unknown_tool"}
