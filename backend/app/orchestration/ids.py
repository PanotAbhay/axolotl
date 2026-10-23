"""Deterministic and random identifiers - owner: Dev 2. SHARED_CONTRACTS §3.

IDs are never derived from model output.
"""

from __future__ import annotations

import hashlib
import secrets

PLAN_PREFIX = "plan_"
RUN_PREFIX = "run_"
VERIFICATION_PREFIX = "ver_"
COUNTEREXAMPLE_PREFIX = "cex_"
ARTEFACT_PREFIX = "art_"

SHORT_ID_BYTES = 6  # 12 hex characters, per §3


def _random(prefix: str) -> str:
    return prefix + secrets.token_hex(SHORT_ID_BYTES)


def new_plan_id() -> str:
    return _random(PLAN_PREFIX)


def new_run_id() -> str:
    return _random(RUN_PREFIX)


def new_verification_id() -> str:
    return _random(VERIFICATION_PREFIX)


def new_counterexample_id() -> str:
    return _random(COUNTEREXAMPLE_PREFIX)


def new_artefact_id() -> str:
    return _random(ARTEFACT_PREFIX)


def case_hash(function: str, args: list, kwargs: dict) -> str:
    """Stable hash of a case's inputs, for `BehaviourCase.case_hash`.

    Deterministic across processes: sorted keys, no randomness, no repr of objects.
    """
    import json

    payload = json.dumps(
        {"function": function, "args": args, "kwargs": kwargs},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]
