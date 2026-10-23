"""Database-aware routes - owner: Dev 3. SHARED_CONTRACTS §9, Spec §11.2.

"If MongoDB is unreachable, endpoints return 503 DATABASE_UNAVAILABLE." `get_db()`
already says so when no URI is configured. This covers the other ways Atlas goes away
while the app is running - nothing listening, a cluster host that does not resolve, a
rejected password - which otherwise surface as driver exceptions and leave as a bare
500 INTERNAL_ERROR that tells the user nothing.

Use it on a router:

    router = APIRouter(tags=["repositories"], route_class=DatabaseAwareRoute)

The message names the exception type only. Driver text lists cluster hostnames and can
echo parts of the connection string.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi.routing import APIRoute
from pymongo.errors import ConfigurationError, ConnectionFailure, OperationFailure
from starlette.requests import Request
from starlette.responses import Response

from app.errors import database_unavailable

# OperationFailure codes that mean "cannot use this database at all", not "this query
# was wrong": 18 AuthenticationFailed, 13 Unauthorized.
_UNUSABLE_CODES = {13, 18}


def is_database_unavailable(exc: BaseException) -> bool:
    if isinstance(exc, ConnectionFailure | ConfigurationError):
        return True
    return isinstance(exc, OperationFailure) and exc.code in _UNUSABLE_CODES


class DatabaseAwareRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def guarded(request: Request) -> Response:
            try:
                return await handler(request)
            except Exception as exc:
                if is_database_unavailable(exc):
                    raise database_unavailable(
                        f"MongoDB is unreachable ({type(exc).__name__})"
                    ) from exc
                raise

        return guarded
