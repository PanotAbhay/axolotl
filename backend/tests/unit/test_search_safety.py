"""Search safety and readiness - owner: Dev 3. No network.

Covers the held-out guard in the chunker, readiness that follows Atlas's `queryable`
flag, and `source_chunk_id` being set once chunks are stored.
"""

import pytest

from app.models.contracts import SymbolRecord
from app.search import chunking, pipeline
from app.search.indexes import classify


def _symbol(path: str, kind: str = "function", name: str = "m.f") -> SymbolRecord:
    return SymbolRecord(
        repository_id="repo_safety000001", snapshot_hash="sha256:s", symbol_id=f"sym_{name}",
        kind=kind, qualified_name=name, module_id="module_m", path=path,
        start_line=1, end_line=2,
    )


@pytest.mark.parametrize("path", [
    "challenge_cases/held_out.py",
    "demo/challenge_cases/held_out.py",
    "demo\\challenge_cases\\held_out.py",
])
def test_held_out_cases_are_never_chunked(path):
    with pytest.raises(chunking.HeldOutLeak):
        chunking.build_chunks([_symbol(path)], {"module_m": "def f():\n    pass\n"})


def test_a_name_merely_containing_the_word_is_fine():
    chunks = chunking.build_chunks(
        [_symbol("not_challenge_cases.py")], {"module_m": "def f():\n    pass\n"}
    )
    assert len(chunks) == 1


@pytest.mark.parametrize(("status", "queryable", "expected"), [
    ("BUILDING", True, "ok"),      # updated definition rebuilding; old one still serves
    ("PENDING", False, "building"),
    ("BUILDING", False, "building"),
    ("READY", True, "ok"),
    ("FAILED", False, "unavailable"),
    ("READY", None, "ok"),         # older responses without `queryable`
    (None, None, "unavailable"),
    # Added on dev2/search-queryable: `queryable` has to win in both directions. A
    # green chip over a search that fails is worse than a cautious 503.
    ("READY", False, "building"),
    # And a failed index needs a rebuild, so it must never read as merely slow,
    # whatever it claims about being queryable.
    ("FAILED", True, "unavailable"),
    ("ready", None, "ok"),         # status case does not matter
])
def test_readiness_follows_what_atlas_says(status, queryable, expected):
    assert classify(status, queryable) == expected


async def test_symbols_point_at_their_stored_chunks(monkeypatch):
    from app import search
    from app.persistence import graphstore

    calls: dict = {}

    async def persist_chunks(repo_id, chunks):
        calls["persisted"] = [c["chunk_id"] for c in chunks]
        return len(chunks)

    async def set_source_chunk_ids(repo_id, chunk_by_symbol):
        calls["linked"] = dict(chunk_by_symbol)
        return len(chunk_by_symbol)

    async def searchable(repository_id, **_):
        return True

    monkeypatch.setattr(search, "persist_chunks", persist_chunks)
    monkeypatch.setattr(graphstore, "set_source_chunk_ids", set_source_chunk_ids)
    monkeypatch.setattr(pipeline, "wait_until_searchable", searchable)

    symbols = [_symbol("m.py", name="m.f"), _symbol("m.py", kind="nested_function",
                                                    name="m.f.inner")]
    result = await pipeline.index_repository(
        "repo_safety000001", symbols, {"module_m": "def f():\n    def inner(): pass\n"},
        enrich=False,
    )

    assert result["chunks"] == 1
    # Only the chunked symbol is linked; nested functions have no chunk of their own.
    assert calls["linked"] == {"sym_m.f": calls["persisted"][0]}


async def test_symbols_are_not_linked_when_chunks_fail_to_store(monkeypatch):
    from app import search
    from app.persistence import graphstore

    linked = []

    async def broken(repo_id, chunks):
        raise RuntimeError("atlas said no")

    async def set_source_chunk_ids(repo_id, chunk_by_symbol):
        linked.append(chunk_by_symbol)

    monkeypatch.setattr(search, "persist_chunks", broken)
    monkeypatch.setattr(graphstore, "set_source_chunk_ids", set_source_chunk_ids)

    result = await pipeline.index_repository(
        "repo_safety000001", [_symbol("m.py")], {"module_m": "def f():\n    pass\n"},
        enrich=False,
    )
    assert linked == []
    assert any("not persisted" in w for w in result["warnings"])
