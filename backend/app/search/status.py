"""Search index readiness - owner: Dev 3. SHARED_CONTRACTS §8 `search_status()`.

Kept as the §8 name. The implementation now lives in `app/search/indexes.py`, beside
the index definitions it reports on, and this delegates to it: three copies of
"is the index ready?" could disagree, and the status chip would then contradict the
search endpoint next to it.

`app.search.search_status` is the same function.
"""

from app.persistence import db
from app.search.indexes import search_status as _search_status


async def search_status() -> dict[str, str]:
    """{"keyword": ..., "vector": ...}, each "ok" | "building" | "unavailable"."""
    # Short-circuit on a dead database rather than asking Atlas for an index list it
    # cannot answer.
    mongo_ok, _ = await db.ping()
    if not mongo_ok:
        return {"keyword": "unavailable", "vector": "unavailable"}
    return await _search_status()
