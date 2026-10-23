"""Search index readiness for GET /system/status - owner: Dev 3.

Dev 2 wrote a standalone version of this while `app.search` did not exist yet. The
indexes now do, so this delegates to `app.search.indexes.search_status()` - the same
function the search endpoints consult. Two implementations of "is the index ready?"
could disagree, and the status chip would then contradict the endpoint next to it.
"""

import logging
from typing import Any

from app.persistence import db
from app.search.indexes import CHUNKS_COLLECTION, search_status

log = logging.getLogger(__name__)


async def search_index_status(mongo_ok: bool) -> dict[str, str]:
    """Each value is "ok" | "unavailable" | "building" (SHARED_CONTRACTS §6)."""
    if not mongo_ok:
        return {"keyword": "unavailable", "vector": "unavailable"}
    return await search_status()


async def describe_indexes() -> list[dict[str, Any]]:
    """Full index documents, for `docs/mongodb-atlas.md` and debugging."""
    database = await db.get_db()
    cursor = await database[CHUNKS_COLLECTION].list_search_indexes()
    return [index async for index in cursor]
