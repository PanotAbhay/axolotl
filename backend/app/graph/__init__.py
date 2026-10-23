"""Dependency graph - owner: Dev 3. SHARED_CONTRACTS §8.

Nodes are rebuilt from the persisted symbols rather than stored separately: §9 lists
no nodes collection, and deriving them means the graph can never disagree with the
symbols it is drawn from.
"""

from __future__ import annotations

import logging

import networkx as nx

from app.analysis.astwalk import looks_like_test
from app.graph.builder import to_networkx
from app.models.contracts import (
    GraphEdge,
    GraphNode,
    GraphPayload,
    ModuleDetail,
    SymbolRecord,
)
from app.persistence import graphstore

log = logging.getLogger(__name__)

FUNCTION_KINDS = frozenset({"function", "async_function", "method", "nested_function"})


async def get_graph(repo_id: str, run_id: str | None = None) -> GraphPayload:
    """SHARED_CONTRACTS §6/§8. With `run_id`, unit statuses are overlaid."""
    repository = await graphstore.get_repository(repo_id)
    symbols = await graphstore.list_symbols(repo_id)
    edges = await graphstore.list_edges(repo_id)

    nodes = _nodes_from_symbols(symbols)
    nodes.extend(_external_nodes(edges, {n.id for n in nodes}))

    if run_id:
        await _overlay_statuses(nodes, run_id)

    return GraphPayload(
        repository_id=repo_id,
        snapshot_hash=repository.snapshot_hash,
        level="module",
        run_id=run_id,
        nodes=sorted(nodes, key=lambda n: n.id),
        edges=edges,
        warnings=list(repository.warnings),
    )


async def load_networkx(repo_id: str) -> nx.DiGraph:
    """The scheduling graph. Local modules and confirmed import edges only.

    Edge A -> B means A depends on B. Dev 2's scheduler reads it that way.
    """
    symbols = await graphstore.list_symbols(repo_id)
    edges = await graphstore.list_edges(repo_id)
    return to_networkx(_nodes_from_symbols(symbols), edges)


async def get_module_detail(repo_id: str, module_id: str) -> ModuleDetail:
    """Everything the module inspector shows for one module."""
    from app.errors import NOT_FOUND, AppError

    symbols = await graphstore.list_symbols(repo_id, module_id=module_id)
    if not symbols:
        raise AppError(
            NOT_FOUND, f"No module {module_id!r}", status_code=404,
            details={"repository_id": repo_id, "module_id": module_id},
        )

    edges = await graphstore.list_edges(repo_id)
    module_symbol = next((s for s in symbols if s.kind == "module"), symbols[0])

    source = await _read_source(repo_id, module_symbol.path)
    warnings = list(module_symbol.analysis_warnings)
    if source is None:
        warnings.append(SOURCE_UNAVAILABLE)

    return ModuleDetail(
        module_id=module_id,
        path=module_symbol.path,
        symbols=symbols,
        imports=[e for e in edges if e.source == module_id],
        dependants=[e for e in edges if e.target == module_id],
        source=source or "",
        warnings=warnings,
        # Visible behaviour cases are Dev 4's; 0 until load_cases is wired up.
        test_case_count=0,
    )


async def get_symbol(repo_id: str, symbol_id: str) -> tuple[SymbolRecord, str]:
    """(record, the source slice it spans) - SHARED_CONTRACTS §8.

    The slice is "" when the snapshot is not on this machine; `get_symbol_detail`
    says so explicitly.
    """
    symbol, source, _ = await get_symbol_detail(repo_id, symbol_id)
    return symbol, source


async def get_symbol_detail(
    repo_id: str, symbol_id: str
) -> tuple[SymbolRecord, str, list[str]]:
    """(record, source slice, warnings) - what the symbol endpoint returns."""
    symbol = await graphstore.get_symbol(repo_id, symbol_id)
    source = await _read_source(repo_id, symbol.path)
    if source is None:
        return symbol, "", [SOURCE_UNAVAILABLE]
    lines = source.splitlines()
    start = max(0, symbol.start_line - 1)
    end = min(len(lines), symbol.end_line)
    return symbol, "\n".join(lines[start:end]), []


async def find_symbol(repo_id: str, qualified_name: str) -> SymbolRecord | None:
    return await graphstore.find_symbol(repo_id, qualified_name)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _nodes_from_symbols(symbols: list[SymbolRecord]) -> list[GraphNode]:
    by_module: dict[str, list[SymbolRecord]] = {}
    for symbol in symbols:
        by_module.setdefault(symbol.module_id, []).append(symbol)

    nodes: list[GraphNode] = []
    for module_id, group in by_module.items():
        module_symbol = next((s for s in group if s.kind == "module"), group[0])
        path = module_symbol.path
        nodes.append(
            GraphNode(
                id=module_id,
                label=path.rsplit("/", 1)[-1],
                kind="test_module" if looks_like_test(path) else "local_module",
                path=path,
                function_count=sum(1 for s in group if s.kind in FUNCTION_KINDS),
                class_count=sum(1 for s in group if s.kind == "class"),
                warnings=list(module_symbol.analysis_warnings),
            )
        )
    return nodes


def _external_nodes(edges: list[GraphEdge], known: set[str]) -> list[GraphNode]:
    """External packages are derived from the edges that reference them."""
    external: dict[str, GraphNode] = {}
    for edge in edges:
        if edge.target in known or not edge.target.startswith("ext_"):
            continue
        external.setdefault(
            edge.target,
            GraphNode(
                id=edge.target,
                label=edge.target.removeprefix("ext_"),
                kind="external_package",
                path=None,
            ),
        )
    return list(external.values())


async def _overlay_statuses(nodes: list[GraphNode], run_id: str) -> None:
    """Paint unit status onto module nodes.

    Dev 2 owns run state, so this calls their mapping rather than recomputing it.
    A stale run_id renders an un-overlaid graph instead of a 404.
    """
    from app.orchestration.overlay import get_graph_overlay, get_unit_statuses_safe

    statuses = await get_unit_statuses_safe(run_id)
    if not statuses:
        return

    overlay = await get_graph_overlay(run_id)
    for node in nodes:
        if node.id in statuses:
            node.status = statuses[node.id]
            node.unit_id = overlay.get(node.id, {}).get("unit_id")


# Snapshots live on the local disk of the machine that imported them (WORKSPACE_ROOT),
# while the graph lives in Atlas. Open a repository imported elsewhere and the graph is
# all there but the source is not - so say that, rather than show an empty file.
SOURCE_UNAVAILABLE = (
    "Source unavailable: this repository's snapshot is not on this machine. "
    "Re-import the repository here to inspect its code."
)


async def _read_source(repo_id: str, relative_path: str) -> str | None:
    """The file's text, or None when the snapshot (or this file in it) is missing."""
    from app.ingestion import snapshot_path

    path = snapshot_path(repo_id) / relative_path
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:  # noqa: BLE001 - reported to the caller as a warning
        log.warning("could not read %s for %s: %s", relative_path, repo_id,
                    type(exc).__name__)
        return None
