"""Indexing pipeline - owner: Dev 3. Spec §8.5.

Turns a persisted snapshot into searchable chunks, in three stages that fail
independently:

  1. build + persist chunks   pure, no network. Keyword search works the moment this
                              finishes, even with no API key at all.
  2. descriptions             one Gemini call per chunk. Failure costs semantic
                              quality, never the chunk.
  3. embeddings               one call per chunk. A chunk with no embedding simply
                              does not take part in vector search.

Stage 1 runs on every import. Stages 2 and 3 are skipped when `INDEX_ON_IMPORT` is
off, and can be run later against a stored snapshot via `reindex_repository`.

Nothing here invents a description or a zero vector to fill a gap: a wrong
description makes search confidently misleading, and a zero vector sits at a fixed
distance from every query and quietly pollutes every result.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.errors import SNAPSHOT_UNAVAILABLE, AppError
from app.models.contracts import SymbolRecord
from app.search.chunking import build_chunks, embedding_text

log = logging.getLogger(__name__)

# Atlas Search is eventually consistent: freshly inserted documents are not searchable
# for a few seconds. Import waits for them, because "I imported it and search found
# nothing" is indistinguishable from a broken search.
SEARCHABLE_TIMEOUT_SECONDS = 45.0
SEARCHABLE_POLL_SECONDS = 1.5


async def index_repository(
    repository_id: str,
    symbols: list[SymbolRecord],
    sources_by_module: dict[str, str],
    *,
    enrich: bool = True,
) -> dict[str, Any]:
    """-> {chunks, described, embedded, warnings}. Never raises."""
    from app.persistence import graphstore
    from app.search import persist_chunks

    warnings: list[str] = []
    chunks = build_chunks(symbols, sources_by_module)
    if not chunks:
        # This early return is also what stops `persist_chunks` below from deleting a
        # repository's existing chunks and replacing them with nothing. Keep it.
        return {"chunks": 0, "described": 0, "embedded": 0,
                "warnings": ["no indexable symbols, so nothing was chunked"]}

    if enrich:
        warnings.extend(await _describe(chunks))
        warnings.extend(await _embed(chunks))
    else:
        warnings.append(
            "descriptions and embeddings were skipped (INDEX_ON_IMPORT is off), so "
            "only keyword search will work for this repository"
        )

    try:
        await persist_chunks(repository_id, chunks)
    except Exception as exc:  # noqa: BLE001 - an un-indexed repository is still usable
        log.warning("could not persist chunks for %s: %s", repository_id, exc)
        return {"chunks": 0, "described": 0, "embedded": 0,
                "warnings": [*warnings, f"chunks were not persisted: {exc}"]}

    # SymbolRecord.source_chunk_id (§4): symbol -> its chunk, set only once the chunk
    # really is stored. Its own try/except, because it is a second write and failing
    # it does not un-store the chunks. Sharing the block above reported a failure here
    # as "chunks were not persisted" with `chunks: 0`, which would send the caller
    # re-running an index that had in fact succeeded.
    try:
        await graphstore.set_source_chunk_ids(
            repository_id, {c["symbol_id"]: c["chunk_id"] for c in chunks}
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("could not link symbols to chunks for %s: %s", repository_id, exc)
        warnings.append(
            f"the chunks were stored, but symbols were not linked back to them "
            f"({exc}); search works, `SymbolRecord.source_chunk_id` is stale"
        )

    if not await wait_until_searchable(repository_id):
        warnings.append(
            "the chunks were stored but are not searchable yet; Atlas Search indexes "
            "new documents a few seconds behind the write, so a search made now may "
            "return nothing"
        )

    described = sum(1 for c in chunks if c.get("description"))
    embedded = sum(1 for c in chunks if c.get("embedding"))
    log.info(
        "indexed %s: %d chunk(s), %d described, %d embedded",
        repository_id, len(chunks), described, embedded,
    )
    return {"chunks": len(chunks), "described": described,
            "embedded": embedded, "warnings": warnings}


async def _describe(chunks: list[dict[str, Any]]) -> list[str]:
    from app.search.descriptions import describe_chunks

    try:
        return await describe_chunks(chunks)
    except Exception as exc:  # noqa: BLE001
        log.warning("describing chunks failed: %s", exc)
        return [f"chunk descriptions failed ({type(exc).__name__})"]


async def _embed(chunks: list[dict[str, Any]]) -> list[str]:
    from app.search.embeddings import embed_documents

    try:
        vectors = await embed_documents([embedding_text(c) for c in chunks])
    except Exception as exc:  # noqa: BLE001
        log.warning("embedding chunks failed: %s", exc)
        return [f"chunk embeddings failed ({type(exc).__name__}), so vector and "
                f"hybrid search will return nothing for this repository"]

    for chunk, vector in zip(chunks, vectors, strict=True):
        chunk["embedding"] = vector

    missing = sum(1 for v in vectors if v is None)
    if missing == len(vectors):
        return ["no chunk was embedded, so vector and hybrid search will return "
                "nothing for this repository"]
    if missing:
        return [f"{missing} of {len(vectors)} chunk(s) could not be embedded and are "
                f"absent from vector search"]
    return []


async def reindex_repository(
    repository_id: str, *, enrich: bool = True
) -> dict[str, Any]:
    """Re-run the whole pipeline from the stored snapshot and symbols.

    `enrich` defaults to True and ignores `INDEX_ON_IMPORT`: asking for a re-index
    explicitly means do the work, whatever the import default is. Tests pass False to
    stay off the network.

    Used by POST /repositories/{repo_id}/index - after an import with enrichment off,
    after a key becomes available, or after the embedding model changes.
    """
    from app.ingestion import snapshot_path
    from app.persistence import graphstore

    await graphstore.get_repository(repository_id)   # 404s if unknown
    symbols = await graphstore.list_symbols(repository_id)
    root = snapshot_path(repository_id)

    # The snapshot is on local disk, not in Atlas, so a repository imported on another
    # machine cannot be re-indexed here. Saying so beats the alternative: every source
    # read fails, `build_chunks` sees no sources and returns nothing, and the caller
    # gets a 200 reading `chunks=0, "no indexable symbols"` - which is wrong twice
    # over, because the symbols are all present and the repository is fine.
    if symbols and not root.is_dir():
        raise AppError(
            SNAPSHOT_UNAVAILABLE,
            "This repository has no snapshot on this machine, so it cannot be "
            "re-indexed here. Snapshots are local to whoever imported the "
            "repository; import it again on this machine to index it.",
            status_code=409,
            details={"repository_id": repository_id, "expected_path": str(root),
                     "symbols": len(symbols)},
        )

    # Sources come from the snapshot, which is immutable, so a re-index describes the
    # same code the symbols were extracted from.
    sources: dict[str, str] = {}
    for symbol in symbols:
        if symbol.module_id in sources:
            continue
        path = root / symbol.path
        if not path.is_file():
            continue
        try:
            sources[symbol.module_id] = path.read_text(encoding="utf-8")
        except OSError as exc:
            log.warning("could not read %s: %s", path, exc)

    return await index_repository(repository_id, symbols, sources, enrich=enrich)


async def wait_until_searchable(
    repository_id: str, *, timeout: float = SEARCHABLE_TIMEOUT_SECONDS
) -> bool:
    """Poll the text index until this repository's chunks appear in it.

    Returns False on timeout rather than raising: the chunks are stored either way,
    and the caller records that search may lag rather than failing the import.
    """
    from app.persistence import db
    from app.search.indexes import CHUNKS_COLLECTION, TEXT_INDEX

    pipeline = [
        {"$search": {
            "index": TEXT_INDEX,
            "equals": {"path": "repository_id", "value": repository_id},
        }},
        {"$limit": 1},
        {"$project": {"_id": 0, "chunk_id": 1}},
    ]

    database = await db.get_db()
    collection = database[CHUNKS_COLLECTION]
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout

    while loop.time() < deadline:
        try:
            rows = [row async for row in await collection.aggregate(pipeline)]
        except Exception as exc:  # noqa: BLE001 - index may still be building
            log.info("waiting for the text index: %s", exc)
            rows = []
        if rows:
            return True
        await asyncio.sleep(SEARCHABLE_POLL_SECONDS)

    log.warning("chunks for %s were not searchable within %.0fs",
                repository_id, timeout)
    return False
