"""Code chunking - owner: Dev 3. Spec §8.5.

One chunk per function, method and class, plus a module-level chunk. Chunks are what
Atlas Search and Vector Search actually index, so their granularity decides whether
"where does the final customer bill get rounded?" can land on a single function
rather than a whole file.

Chunk ids are deterministic: the same snapshot always yields the same ids, so
re-importing does not orphan anything that referenced them. They are derived from the
snapshot hash and the symbol id, neither of which includes the repository, so two
imports of the same fixture share chunk ids. They are unique **within** a repository
- the `(repository_id, chunk_id)` index says so - exactly as `symbol_id` already is.
Do not treat a bare `chunk_id` as a global key.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import PurePosixPath
from typing import Any

from app.models.contracts import SymbolRecord

log = logging.getLogger(__name__)

CHUNK_PREFIX = "chunk_"

# A module chunk exists so a query can match a file's overall purpose, not only its
# individual definitions.
CHUNKED_KINDS = frozenset({"function", "async_function", "method", "class", "module"})

MAX_CHUNK_CHARS = 8000   # keeps a huge generated file from dominating the index

# Held-out behaviour cases (Dev 4) must never become searchable. They live outside the
# fixture tree and ingestion already refuses a tree that contains them; this is the
# second lock on the same door, at the point where text enters the index.
HELD_OUT_DIRECTORY = "challenge_cases"


class HeldOutLeak(RuntimeError):
    """A held-out case file reached the chunker. Nothing from it is indexed."""


def chunk_id_for(snapshot_hash: str, symbol_id: str) -> str:
    payload = f"{snapshot_hash}\0{symbol_id}".encode()
    return CHUNK_PREFIX + hashlib.sha256(payload).hexdigest()[:16]


def slice_source(source: str, start_line: int, end_line: int) -> str:
    lines = source.splitlines()
    start = max(0, start_line - 1)
    end = min(len(lines), max(end_line, start_line))
    return "\n".join(lines[start:end])[:MAX_CHUNK_CHARS]


def identifiers_of(symbol: SymbolRecord) -> str:
    """The names worth matching on, separate from the body.

    `qualified_name` plus decorators and bases: a query for `apply_discount` or for a
    base class should hit even when the body does not repeat the word.
    """
    parts = [symbol.qualified_name, symbol.qualified_name.split(".")[-1]]
    parts.extend(symbol.decorators)
    parts.extend(symbol.bases)
    if symbol.signature:
        parts.append(symbol.signature)
    return " ".join(p for p in parts if p)


def build_chunks(
    symbols: list[SymbolRecord], sources_by_module: dict[str, str]
) -> list[dict[str, Any]]:
    """One chunk per indexable symbol. `description` and `embedding` are filled later."""
    chunks: list[dict[str, Any]] = []

    for symbol in symbols:
        if HELD_OUT_DIRECTORY in PurePosixPath(symbol.path.replace("\\", "/")).parts:
            raise HeldOutLeak(f"refusing to chunk held-out path {symbol.path!r}")
        if symbol.kind not in CHUNKED_KINDS:
            continue
        source = sources_by_module.get(symbol.module_id, "")
        if not source:
            continue

        body = slice_source(source, symbol.start_line, symbol.end_line)
        if not body.strip():
            continue

        chunks.append({
            "chunk_id": chunk_id_for(symbol.snapshot_hash, symbol.symbol_id),
            "repository_id": symbol.repository_id,
            "snapshot_hash": symbol.snapshot_hash,
            "symbol_id": symbol.symbol_id,
            "module_id": symbol.module_id,
            "qualified_name": symbol.qualified_name,
            "kind": symbol.kind,
            "path": symbol.path,
            "start_line": symbol.start_line,
            "end_line": symbol.end_line,
            "source": body,
            "identifiers": identifiers_of(symbol),
            # Untrusted: a docstring can say anything. Indexed as text, never obeyed.
            "docstring": symbol.docstring or "",
            "description": None,
            "embedding": None,
        })

    log.info("built %d chunk(s) from %d symbol(s)", len(chunks), len(symbols))
    return chunks


def embedding_text(chunk: dict[str, Any]) -> str:
    """What gets embedded: description + identifiers + source.

    The description leads because it is natural language, which is what a natural
    language query is closest to. Identifiers follow so exact names still pull their
    weight, and the source last for everything neither captures.
    """
    parts = [
        chunk.get("description") or "",
        chunk.get("identifiers") or "",
        chunk.get("docstring") or "",
        chunk.get("source") or "",
    ]
    return "\n".join(p for p in parts if p)[:MAX_CHUNK_CHARS]
