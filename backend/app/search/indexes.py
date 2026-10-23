"""Atlas Search and Vector Search indexes - owner: Dev 3. SHARED_CONTRACTS §9.

Two indexes on `code_chunks`:

  `code_chunks_text`    Atlas Search, for keyword queries
  `code_chunks_vector`  Vector Search, for semantic queries

Both build **asynchronously**. Creating them returns immediately and readiness takes
anywhere from seconds to minutes, which is why `search_status()` exists and why search
endpoints return 503 `SEARCH_INDEX_NOT_READY` rather than quietly returning nothing
while a build is in flight. An empty result set and "the index is not ready" are very
different answers and must not look the same.

Three things about the text index were established by running it, not by reading docs:

  - `lucene.standard` does **not** split `pricing.finalise_amount` on the dot. It
    indexes the whole dotted name as a single token, so a search for `finalise_amount`
    did not match that field at all, and `finalise` matched nothing anywhere. Hence
    the custom `identifier_parts` analyser, which splits on every non-alphanumeric
    character: `pricing.finalise_amount` becomes `pricing`, `finalise`, `amount`,
    which is how people actually search for code (T-06).
  - Listing two `string` definitions for one field is rejected outright - the first
    build of this index failed with *"field contained multiple [string] type
    definitions"* - and a FAILED index is not queryable at all. Alternate analysers
    go in `multi`.
  - `lucene.keyword` over the whole `qualified_name` is still worth having, in
    `multi`, so a fully-qualified query lands exactly rather than merely well.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.search.embeddings import expected_dimensions

log = logging.getLogger(__name__)

CHUNKS_COLLECTION = "code_chunks"
TEXT_INDEX = "code_chunks_text"
VECTOR_INDEX = "code_chunks_vector"

READY_STATUSES = frozenset({"READY", "STALE"})
BUILDING_STATUSES = frozenset({"PENDING", "BUILDING", "IN_PROGRESS"})
FAILED_STATUSES = frozenset({"FAILED", "DOES_NOT_EXIST", "DELETING"})

DROP_TIMEOUT_SECONDS = 30.0

# Splits an identifier into the words it is built from, so that both
# `finalise_amount` and `pricing.finalise_amount` find `pricing.finalise_amount`.
IDENTIFIER_ANALYSER = "identifier_parts"


def text_index_definition() -> dict[str, Any]:
    identifier_field = {
        "type": "string",
        "analyzer": IDENTIFIER_ANALYSER,
        "multi": {
            # The whole value as one token, for an exact fully-qualified match.
            "exact": {"type": "string", "analyzer": "lucene.keyword"},
            # Prose rules, for a query that is a sentence rather than a name.
            "prose": {"type": "string", "analyzer": "lucene.standard"},
        },
    }
    return {
        "analyzers": [
            {
                "name": IDENTIFIER_ANALYSER,
                "tokenizer": {"type": "regexSplit", "pattern": "[^a-zA-Z0-9]+"},
                "tokenFilters": [{"type": "lowercase"}],
            }
        ],
        "mappings": {
            # Explicit rather than dynamic: `embedding` is 768 floats and indexing it
            # as text would bloat the index for no benefit.
            "dynamic": False,
            "fields": {
                "repository_id": {"type": "token"},
                "qualified_name": identifier_field,
                "identifiers": identifier_field,
                "description": {"type": "string", "analyzer": "lucene.standard"},
                "docstring": {"type": "string", "analyzer": "lucene.standard"},
                "source": {"type": "string", "analyzer": "lucene.standard"},
                "path": {"type": "string", "analyzer": "lucene.keyword"},
            },
        },
    }


def vector_index_definition() -> dict[str, Any]:
    return {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": expected_dimensions(),
                "similarity": "cosine",
            },
            # Filtering by repository in the vector stage itself, rather than after,
            # so one repository's chunks cannot crowd out another's.
            {"type": "filter", "path": "repository_id"},
        ]
    }


async def ensure_search_indexes() -> dict[str, str]:
    """Create, repair or update both indexes. Idempotent; returns each one's status.

    Never raises: a tier that forbids driver-side creation, or a transient Atlas
    error, must not stop the app booting. The status is reported instead.
    """
    from pymongo.operations import SearchIndexModel

    from app.persistence import db

    database = await db.get_db()
    collection = database[CHUNKS_COLLECTION]

    # Atlas refuses to create a search index on a collection that does not exist:
    # `NamespaceNotFound: Collection '<db>.code_chunks' does not exist.` On a brand
    # new database that is the state at startup, and the failure is only a log line,
    # so search would report `unavailable` until the next restart after a first
    # import. It works today only because `persistence.indexes.ensure_indexes()`
    # happens to run first in the lifespan and creates the collection - an ordering
    # dependency nothing states and nothing enforces.
    try:
        await database.create_collection(CHUNKS_COLLECTION)
        log.info("created collection %s", CHUNKS_COLLECTION)
    except Exception as exc:  # noqa: BLE001 - almost always "already exists"
        log.debug("collection %s not created: %s", CHUNKS_COLLECTION, exc)

    live = await _live_indexes(collection)
    if live is None:
        return {"keyword": "unavailable", "vector": "unavailable"}

    wanted = [
        (TEXT_INDEX, text_index_definition(), "search"),
        (VECTOR_INDEX, vector_index_definition(), "vectorSearch"),
    ]
    for name, definition, kind in wanted:
        current = live.get(name)

        if current is not None and current["status"] not in FAILED_STATUSES:
            # An index whose definition has moved on is worse than a missing one: it
            # keeps answering queries under the old rules and nothing says so.
            if current["definition"] != definition:
                log.info("search index %s is out of date; updating it", name)
                try:
                    await collection.update_search_index(name, definition)
                    live[name] = {**current, "status": "PENDING"}
                except Exception as exc:  # noqa: BLE001
                    log.warning("could not update %s: %s", name, exc)
            continue

        # A failed index is not queryable and never retries by itself, so skipping it
        # because the name exists would leave search permanently dead with no way back
        # short of the Atlas UI. Dropping and recreating is the recovery path; the
        # index holds no data of its own, only a derived view of `code_chunks`.
        if current is not None:
            log.warning("search index %s is %s; dropping it to rebuild",
                        name, current["status"])
            try:
                await collection.drop_search_index(name)
                await _wait_until_gone(collection, name)
            except Exception as exc:  # noqa: BLE001
                log.warning("could not drop failed index %s: %s", name, exc)
                continue

        try:
            await collection.create_search_index(
                SearchIndexModel(definition=definition, name=name, type=kind)
            )
            live[name] = {"status": "PENDING", "queryable": False,
                          "definition": definition}
            log.info("created %s index %s (builds asynchronously)", kind, name)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "could not create %s: %s. Create it in the Atlas UI if the tier "
                "forbids driver-side creation; the definition is in "
                "app/search/indexes.py", name, exc,
            )

    return {
        "keyword": _classify_entry(live.get(TEXT_INDEX)),
        "vector": _classify_entry(live.get(VECTOR_INDEX)),
    }


async def _live_indexes(collection: Any) -> dict[str, dict[str, Any]] | None:
    """Name -> {status, definition}. None when Atlas cannot be asked at all."""
    try:
        cursor = await collection.list_search_indexes()
        return {
            str(index.get("name")): {
                "status": str(index.get("status", "")).upper(),
                "queryable": index.get("queryable"),
                "definition": index.get("latestDefinition") or {},
            }
            async for index in cursor
        }
    except Exception as exc:  # noqa: BLE001
        log.warning("could not list search indexes: %s", exc)
        return None


def _classify_entry(entry: dict[str, Any] | None) -> str:
    if entry is None:
        return "unavailable"
    return classify(entry.get("status"), entry.get("queryable"))


async def _wait_until_gone(collection: Any, name: str) -> None:
    """A drop is asynchronous, and creating over a half-dropped index fails."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + DROP_TIMEOUT_SECONDS
    while loop.time() < deadline:
        cursor = await collection.list_search_indexes()
        names = {str(i.get("name")) async for i in cursor}
        if name not in names:
            return
        await asyncio.sleep(1.0)
    log.warning("index %s was still present %.0fs after the drop", name,
                DROP_TIMEOUT_SECONDS)


def classify(status: str | None, queryable: bool | None = None) -> str:
    """Atlas's own status, mapped to ok | building | unavailable.

    `queryable` wins when Atlas reports it, in **both** directions:

    - while an *updated* definition rebuilds, the status reads BUILDING but Atlas
      keeps serving the previous version, so search still works and must not answer
      503 (Dev 3);
    - and an index Atlas says is not queryable must never read as ready, whatever its
      status claims. That direction is the easier one to miss: it would show a green
      chip over a search that fails.

    `status` alone is the fallback, for a response shape that omits the field.
    """
    if status is None:
        return "unavailable"

    status = status.upper()
    # Before `queryable`, because a failed index needs a rebuild and must never read
    # as merely slow.
    if status in FAILED_STATUSES:
        return "unavailable"
    if queryable is True:
        return "ok"
    if queryable is False:
        # Atlas is explicit that it cannot be searched yet. Not a failure: either
        # still building, or briefly between definitions.
        return "building"

    if status in READY_STATUSES:
        return "ok"
    if status in BUILDING_STATUSES:
        return "building"
    return "unavailable"


async def search_status() -> dict[str, str]:
    """SHARED_CONTRACTS §8. Dev 2 surfaces this in /system/status."""
    from app.persistence import db

    try:
        database = await db.get_db()
        cursor = await database[CHUNKS_COLLECTION].list_search_indexes()
        found = {
            str(i.get("name")): (str(i.get("status", "")).upper(), i.get("queryable"))
            async for i in cursor
        }
    except Exception:  # noqa: BLE001 - reported as a status, never raised
        return {"keyword": "unavailable", "vector": "unavailable"}

    return {
        "keyword": classify(*found.get(TEXT_INDEX, (None, None))),
        "vector": classify(*found.get(VECTOR_INDEX, (None, None))),
    }


async def supports_native_hybrid() -> bool:
    """`$rankFusion` needs MongoDB 8.0+. Ours is 8.0.34, so this should be True.

    Checked rather than assumed: the answer is reported to the user as
    `native_hybrid`, and claiming native fusion while running a Python fallback would
    be a quiet lie about how the result was produced.
    """
    from app.persistence import db

    version = await db.server_version()
    if not version:
        return False
    try:
        major, minor = (int(p) for p in version.split(".")[:2])
    except ValueError:
        return False
    return (major, minor) >= (8, 0)
