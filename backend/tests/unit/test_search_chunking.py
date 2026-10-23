"""Chunking and index definitions - owner: Dev 3. Offline, no Atlas, no Gemini.

Chunking decides what search can possibly find: a chunk per function means a query
can land on `finalise_amount` rather than on all of `pricing.py`. These tests pin
that granularity, the determinism of chunk ids, and the two index definitions whose
details T-06 and T-07 depend on.
"""

from app.analysis.astwalk import analyse_module
from app.search.chunking import (
    CHUNKED_KINDS,
    MAX_CHUNK_CHARS,
    build_chunks,
    chunk_id_for,
    embedding_text,
    identifiers_of,
    slice_source,
)
from app.search.indexes import classify, text_index_definition, vector_index_definition


def analyse(tmp_path, source: str, name: str = "pricing.py"):
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return analyse_module(
        source_path=path, relative_path=name,
        repository_id="repo_test", snapshot_hash="sha256:abc",
    )


SAMPLE = '''"""Order pricing."""

TAX = 0.2


@staticmethod
def finalise_amount(lines, category):
    """Round the taxed total to the penny."""
    return sum(lines) * (1 + TAX)


class Ledger(dict):
    def record(self, amount):
        return amount
'''


def test_chunk_ids_are_deterministic_for_the_same_snapshot():
    first = chunk_id_for("sha256:abc", "sym_1")
    assert first == chunk_id_for("sha256:abc", "sym_1")
    assert first != chunk_id_for("sha256:def", "sym_1")
    assert first != chunk_id_for("sha256:abc", "sym_2")
    assert first.startswith("chunk_")


def test_every_function_class_and_module_becomes_its_own_chunk(tmp_path):
    analysis = analyse(tmp_path, SAMPLE)
    chunks = build_chunks(analysis.symbols, {analysis.module_id: analysis.source})

    names = {c["qualified_name"] for c in chunks}
    assert "pricing.finalise_amount" in names
    assert "pricing.Ledger" in names
    assert "pricing.Ledger.record" in names
    # The module chunk lets a query match a file's overall purpose.
    assert any(c["kind"] == "module" for c in chunks)
    assert {c["kind"] for c in chunks} <= CHUNKED_KINDS


def test_a_chunk_carries_the_lines_of_its_own_definition(tmp_path):
    analysis = analyse(tmp_path, SAMPLE)
    chunks = build_chunks(analysis.symbols, {analysis.module_id: analysis.source})
    chunk = next(c for c in chunks if c["qualified_name"] == "pricing.finalise_amount")

    assert "def finalise_amount" in chunk["source"]
    # Not the whole file: a chunk that spilled into its neighbours would make every
    # query match everything.
    assert "class Ledger" not in chunk["source"]
    assert chunk["start_line"] <= chunk["end_line"]
    assert chunk["description"] is None   # filled later, never invented here
    assert chunk["embedding"] is None


def test_decorators_and_bases_are_searchable_identifiers(tmp_path):
    analysis = analyse(tmp_path, SAMPLE)
    by_name = {s.qualified_name: s for s in analysis.symbols}

    assert "staticmethod" in identifiers_of(by_name["pricing.finalise_amount"])
    assert "dict" in identifiers_of(by_name["pricing.Ledger"])
    # The bare name as well as the dotted one, so a search for `finalise_amount` hits.
    assert "finalise_amount" in identifiers_of(by_name["pricing.finalise_amount"])


def test_a_module_with_no_source_is_skipped_rather_than_chunked_empty(tmp_path):
    analysis = analyse(tmp_path, SAMPLE)
    assert build_chunks(analysis.symbols, {}) == []


def test_slicing_is_clamped_to_the_file(tmp_path):
    assert slice_source("a\nb\nc", 1, 99) == "a\nb\nc"
    assert slice_source("a\nb\nc", 0, 1) == "a"
    assert slice_source("", 1, 5) == ""
    assert len(slice_source("x\n" * 20000, 1, 20000)) <= MAX_CHUNK_CHARS


def test_what_gets_embedded_leads_with_natural_language():
    text = embedding_text({
        "description": "Works out what a customer finally owes.",
        "identifiers": "finalise_amount",
        "docstring": "Round the taxed total.",
        "source": "def finalise_amount(): ...",
    })
    # The description first, because a natural-language query is closest to it.
    assert text.startswith("Works out what a customer finally owes.")
    assert "finalise_amount" in text


def test_embedding_text_survives_a_chunk_with_no_description():
    text = embedding_text({"identifiers": "finalise_amount", "source": "def f(): ..."})
    assert "finalise_amount" in text
    assert not text.startswith("\n")


# --- index definitions: the details T-06 and T-07 rest on ---

def test_a_name_is_indexed_by_its_parts_as_well_as_whole():
    """T-06 depends on this and `lucene.standard` alone does not provide it.

    Standard analysis keeps `pricing.finalise_amount` as one token, so a search for
    `finalise_amount` found nothing in that field. The custom analyser splits on
    every non-alphanumeric character, which is how people search for code.

    The shape matters too: two `string` definitions for one field is rejected with
    "field contained multiple [string] type definitions", and the resulting index is
    FAILED, not queryable. Alternate analysers go in `multi`.
    """
    definition = text_index_definition()
    field = definition["mappings"]["fields"]["qualified_name"]

    assert not isinstance(field, list)
    assert field["analyzer"] == "identifier_parts"                  # parts (T-06)
    assert field["multi"]["exact"]["analyzer"] == "lucene.keyword"  # whole, exactly
    assert field["multi"]["prose"]["analyzer"] == "lucene.standard"  # sentences

    analyser = next(a for a in definition["analyzers"]
                    if a["name"] == "identifier_parts")
    assert analyser["tokenizer"] == {
        "type": "regexSplit", "pattern": "[^a-zA-Z0-9]+"
    }
    # Lowercased, so a query for `Finalise_Amount` still matches.
    assert {f["type"] for f in analyser["tokenFilters"]} == {"lowercase"}


def test_identifiers_are_split_the_same_way_as_names():
    fields = text_index_definition()["mappings"]["fields"]
    assert fields["identifiers"]["analyzer"] == "identifier_parts"


def test_the_text_index_does_not_index_the_embedding():
    mappings = text_index_definition()["mappings"]
    assert mappings["dynamic"] is False
    assert "embedding" not in mappings["fields"]


def test_the_vector_index_matches_the_configured_dimensions():
    from app.search.embeddings import expected_dimensions

    fields = vector_index_definition()["fields"]
    vector = next(f for f in fields if f["type"] == "vector")
    assert vector["numDimensions"] == expected_dimensions()
    assert vector["similarity"] == "cosine"
    # Filtering by repository inside the stage, so one repository's chunks cannot
    # crowd out another's.
    assert any(f == {"type": "filter", "path": "repository_id"} for f in fields)


def test_a_building_index_is_not_reported_as_ready():
    """Status alone, for a response that omits `queryable`."""
    assert classify("READY") == "ok"
    assert classify("STALE") == "ok"      # usable, just behind
    assert classify("PENDING") == "building"
    assert classify("BUILDING") == "building"
    assert classify("FAILED") == "unavailable"
    assert classify(None) == "unavailable"


def test_queryable_wins_over_the_status_in_both_directions():
    """`test_search_safety.py` parametrises this; these are the two edges it needs.

    A green chip over a search that fails is worse than a cautious 503, so an index
    Atlas says is not queryable must never read as ready - even one claiming READY.
    And a failed index needs a rebuild, so it must never read as merely slow.
    """
    assert classify("READY", queryable=False) == "building"
    assert classify("FAILED", queryable=True) == "unavailable"
