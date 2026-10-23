"""Repository / symbol / edge persistence - owner: Dev 3. SHARED_CONTRACTS §9.

Collections: `repositories`, `symbols`, `edges`. (`code_chunks` belongs to the search
layer and is deliberately not touched here.)

No in-memory fallback anywhere: with Atlas unreachable `get_db()` raises 503
DATABASE_UNAVAILABLE and every caller fails honestly (§9, Spec §11.2 - disabling Atlas
must break the journeys rather than silently degrade).
"""

from __future__ import annotations

import logging
from typing import Any

from app.errors import NOT_FOUND, AppError
from app.models.contracts import GraphEdge, RepositoryRecord, SymbolRecord
from app.persistence import db

log = logging.getLogger(__name__)

REPOSITORIES = "repositories"
SYMBOLS = "symbols"
EDGES = "edges"


async def save_repository(record: RepositoryRecord) -> RepositoryRecord:
    database = await db.get_db()
    await database[REPOSITORIES].replace_one(
        {"repository_id": record.repository_id}, record.model_dump(), upsert=True
    )
    return record


async def get_repository(repo_id: str) -> RepositoryRecord:
    database = await db.get_db()
    document = await database[REPOSITORIES].find_one(
        {"repository_id": repo_id}, {"_id": 0}
    )
    if document is None:
        raise AppError(
            NOT_FOUND, f"No repository {repo_id!r}", status_code=404,
            details={"repository_id": repo_id},
        )
    return RepositoryRecord(**document)


async def list_repositories() -> list[RepositoryRecord]:
    database = await db.get_db()
    cursor = database[REPOSITORIES].find({}, {"_id": 0}).sort("created_at", -1)
    return [RepositoryRecord(**document) async for document in cursor]


async def replace_symbols(repo_id: str, symbols: list[SymbolRecord]) -> int:
    """Replace this repository's symbols wholesale.

    An import is atomic from the reader's point of view: delete then insert, so a
    partially-reanalysed repository never serves a mix of two snapshots.
    """
    database = await db.get_db()
    await database[SYMBOLS].delete_many({"repository_id": repo_id})
    if symbols:
        await database[SYMBOLS].insert_many([s.model_dump() for s in symbols])
    return len(symbols)


async def replace_edges(repo_id: str, edges: list[GraphEdge]) -> int:
    database = await db.get_db()
    await database[EDGES].delete_many({"repository_id": repo_id})
    if edges:
        await database[EDGES].insert_many(
            [{**e.model_dump(), "repository_id": repo_id} for e in edges]
        )
    return len(edges)


async def set_source_chunk_ids(repo_id: str, chunk_by_symbol: dict[str, str]) -> int:
    """Point each symbol at its search chunk. Symbols without a chunk are cleared."""
    from pymongo import UpdateOne

    database = await db.get_db()
    await database[SYMBOLS].update_many(
        {"repository_id": repo_id}, {"$set": {"source_chunk_id": None}}
    )
    if not chunk_by_symbol:
        return 0
    result = await database[SYMBOLS].bulk_write([
        UpdateOne({"repository_id": repo_id, "symbol_id": symbol_id},
                  {"$set": {"source_chunk_id": chunk_id}})
        for symbol_id, chunk_id in chunk_by_symbol.items()
    ], ordered=False)
    return result.modified_count


async def list_symbols(repo_id: str, module_id: str | None = None) -> list[SymbolRecord]:
    database = await db.get_db()
    query: dict[str, Any] = {"repository_id": repo_id}
    if module_id:
        query["module_id"] = module_id
    cursor = database[SYMBOLS].find(query, {"_id": 0}).sort("start_line", 1)
    return [SymbolRecord(**document) async for document in cursor]


async def get_symbol(repo_id: str, symbol_id: str) -> SymbolRecord:
    database = await db.get_db()
    document = await database[SYMBOLS].find_one(
        {"repository_id": repo_id, "symbol_id": symbol_id}, {"_id": 0}
    )
    if document is None:
        raise AppError(
            NOT_FOUND, f"No symbol {symbol_id!r}", status_code=404,
            details={"repository_id": repo_id, "symbol_id": symbol_id},
        )
    return SymbolRecord(**document)


async def find_symbol(repo_id: str, qualified_name: str) -> SymbolRecord | None:
    database = await db.get_db()
    document = await database[SYMBOLS].find_one(
        {"repository_id": repo_id, "qualified_name": qualified_name}, {"_id": 0}
    )
    return SymbolRecord(**document) if document else None


async def list_edges(repo_id: str) -> list[GraphEdge]:
    database = await db.get_db()
    cursor = database[EDGES].find(
        {"repository_id": repo_id}, {"_id": 0, "repository_id": 0}
    ).sort([("source", 1), ("target", 1)])
    return [GraphEdge(**document) async for document in cursor]
