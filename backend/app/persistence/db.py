"""Mongo client - owner: Dev 3 (minimal implementation by Dev 2 to unblock the skeleton).

DELIBERATE DEVIATION from SHARED_CONTRACTS §2/§8: this uses PyMongo's built-in async
client (`AsyncMongoClient`, pymongo>=4.9) instead of Motor, which reached end of life in
May 2026. The §8 signature is otherwise unchanged; only the return type differs
(`AsyncDatabase` in place of `AsyncIOMotorDatabase`). See BUILD_LOG.md.

Dev 3 owns this package and should extend it (indexes.py, base repo helpers) rather than
work around it. There is deliberately NO in-memory fallback: §9 requires a 503
DATABASE_UNAVAILABLE when Atlas is unreachable.
"""

import logging
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.config import Settings
from app.errors import database_unavailable

log = logging.getLogger(__name__)

_client: AsyncMongoClient[dict[str, Any]] | None = None
_database_name: str = "axolotl"


async def connect(settings: Settings) -> None:
    """Create the client. Lazy: PyMongo does not open sockets until the first operation,
    so a missing or wrong URI never stops the app from booting."""
    global _client, _database_name
    _database_name = settings.mongodb_database

    if not settings.mongodb_uri:
        log.warning("MONGODB_URI is not set - /system/status will report mongodb=unavailable")
        _client = None
        return

    _client = AsyncMongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        appname="axolotl-backend",
        # SHARED_CONTRACTS §0.8: timezone-aware datetimes, UTC in the DB. Without
        # this PyMongo hands back naive datetimes and comparisons silently break -
        # and UK clocks go back at 02:00 on Sun 25 Oct, mid-hackathon.
        tz_aware=True,
    )
    log.info("Mongo client created for database %r", _database_name)


async def disconnect() -> None:
    global _client
    if _client is not None:
        await _client.close()
        log.info("Mongo client closed")
    _client = None


async def get_db() -> AsyncDatabase[dict[str, Any]]:
    """SHARED_CONTRACTS §8. Raises 503 DATABASE_UNAVAILABLE when there is no client."""
    if _client is None:
        raise database_unavailable("MONGODB_URI is not configured")
    return _client[_database_name]


async def ping() -> tuple[bool, str | None]:
    """Real `ping` against Atlas. Returns (ok, error_message).

    The message is the exception type only. Driver error text lists the cluster's
    hostnames and can echo URI fragments, and this string ends up in the public
    `/system/status` response.
    """
    if _client is None:
        return False, "MONGODB_URI is not configured"
    try:
        await _client.admin.command("ping")
        return True, None
    except Exception as exc:  # noqa: BLE001 - surfaced as a status string, never raised
        return False, f"MongoDB ping failed ({type(exc).__name__})"


async def server_version() -> str | None:
    """Atlas cluster version. Native $rankFusion needs 8.0+, $scoreFusion 8.2+."""
    if _client is None:
        return None
    try:
        info = await _client.admin.command("buildInfo")
        return str(info.get("version")) or None
    except Exception:  # noqa: BLE001
        return None
