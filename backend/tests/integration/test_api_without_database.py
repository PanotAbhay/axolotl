"""API behaviour with no database - owner: Dev 2. SHARED_CONTRACTS §9.

"If MongoDB is unreachable, endpoints return 503 DATABASE_UNAVAILABLE. No in-memory
fallback." These tests run with an empty .env, which is exactly that situation, and
pin two things:

  - nothing degrades into a 500 or, worse, a fabricated empty success
  - validation that needs no database still works, so T-08 holds even when Atlas is down

They need no external service and are safe to run anywhere.
"""

import pytest
from fastapi.testclient import TestClient

from app.persistence import db
from tests.conftest import API


@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    """Force the no-database state, rather than relying on `.env` being empty.

    These tests used to pass only because no `MONGODB_URI` was configured. That
    made them green in CI and **red on any correctly configured machine** - every
    teammate who filled in `.env` would see twelve failures in a file describing
    behaviour that had not changed. A test whose premise depends on ambient config
    is testing the machine, not the code.

    Dropping the client is the real mechanism: `get_db()` then raises 503 and
    `ping()` reports unavailable, exactly as an Atlas outage would.
    """
    monkeypatch.setattr(db, "_client", None)

DB_BACKED = [
    ("get", f"{API}/plans/plan_000000000001", None),
    ("get", f"{API}/runs/run_000000000001", None),
    ("get", f"{API}/runs/run_000000000001/events", None),
    ("get", f"{API}/runs/run_000000000001/report", None),
    ("get", f"{API}/runs/run_000000000001/artefacts", None),
    ("get", f"{API}/runs/run_000000000001/units/unit_pricing", None),
    ("get", f"{API}/runs/run_000000000001/diff", None),
    ("post", f"{API}/plans/plan_000000000001/approve", {"approved": True}),
    ("post", f"{API}/plans/plan_000000000001/runs", None),
    ("post", f"{API}/runs/run_000000000001/cancel", None),
]


@pytest.mark.parametrize(("method", "path", "body"), DB_BACKED)
def test_database_backed_endpoints_return_503(client: TestClient, method, path, body):
    response = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)

    assert response.status_code == 503, f"{method} {path} gave {response.status_code}"
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"


@pytest.mark.parametrize(("method", "path", "body"), DB_BACKED)
def test_no_endpoint_fakes_a_success_without_a_database(
    client: TestClient, method, path, body
):
    """A silent empty 200 would be the worst outcome: it reads as 'nothing to report'."""
    response = getattr(client, method)(path, json=body) if body else getattr(client, method)(path)
    assert response.status_code != 200
    assert response.status_code < 500 or response.status_code == 503


def test_unsupported_target_is_rejected_before_the_database_is_touched(
    client: TestClient,
):
    """T-08 must hold even with Atlas down - validation comes first."""
    response = client.post(
        f"{API}/repositories/repo_000000000001/plans", json={"target_id": "python2_to_3"}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "UNSUPPORTED_TARGET"
    assert body["error"]["details"]["reason"]


def test_unknown_target_is_rejected_before_the_database_is_touched(client: TestClient):
    response = client.post(
        f"{API}/repositories/repo_000000000001/plans", json={"target_id": "cobol_to_rust"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNSUPPORTED_TARGET"


def test_a_supported_target_fails_on_the_missing_graph_not_silently(client: TestClient):
    """Dev 3's graph is not wired yet, so this is 503 with a reason - never a fake plan."""
    response = client.post(
        f"{API}/repositories/repo_000000000001/plans",
        json={"target_id": "modern_python3"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] in {
        "INTEGRATION_UNAVAILABLE", "DATABASE_UNAVAILABLE",
    }


def test_malformed_plan_request_is_a_422_envelope(client: TestClient):
    response = client.post(f"{API}/repositories/repo_1/plans", json={"wrong": "field"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_endpoints_needing_no_database_still_work(client: TestClient):
    assert client.get(f"{API}/health").status_code == 200
    assert client.get(f"{API}/migration-targets").status_code == 200
    assert client.get(f"{API}/system/status").status_code == 200


def test_system_status_reports_the_database_as_unavailable(client: TestClient):
    """The status endpoint is the one place that must answer while everything is down."""
    body = client.get(f"{API}/system/status").json()
    assert body["mongodb"] == "unavailable"


def test_an_unexpected_error_still_gets_the_contract_envelope(monkeypatch):
    """A reachable-but-failing Atlas (auth error, timeout mid-query) used to return a
    bare FastAPI 500 that clients cannot parse, having been promised one error shape.

    `raise_server_exceptions=False` makes TestClient return the response the server
    would actually send instead of re-raising.
    """
    from app.main import create_app
    from app.orchestration import store as store_module

    async def explode(run_id):
        raise RuntimeError("simulated Atlas failure with secret in the text")

    monkeypatch.setattr(store_module, "get_run", explode)

    with TestClient(create_app(), raise_server_exceptions=False) as raw:
        response = raw.get(f"{API}/runs/run_000000000001")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert set(body["error"]) == {"code", "message", "details"}
    # The exception's text can carry a connection string, so only its type is shown.
    assert "secret" not in body["error"]["message"]
    assert body["error"]["message"] == "Unexpected RuntimeError"


def test_held_out_counterexamples_are_redacted_for_the_human_view():
    """The unit endpoint is a read path like any other: a sealed held-out case must
    not leak its inputs there."""
    from app.api.plans_runs import _redact_held_out

    sealed = _redact_held_out({
        "case_id": "hcase_001", "visibility": "held_out", "exposed_to_model": False,
        "function": "pricing.finalise_amount", "args": [[{"unit_price": "2.45"}]],
        "kwargs": {}, "old": {"value": "2.65"}, "new": {"value": "2.64"},
    })
    assert "2.45" not in str(sealed)
    assert "2.65" not in str(sealed)
    assert sealed["redacted"] is True
    assert sealed["case_id"] == "hcase_001"   # the id itself is fine to show


def test_an_exposed_held_out_case_is_shown_in_full():
    from app.api.plans_runs import _redact_held_out

    exposed = _redact_held_out({
        "case_id": "hcase_001", "visibility": "held_out", "exposed_to_model": True,
        "args": [[{"unit_price": "2.45"}]], "old": {"value": "2.65"},
    })
    assert "2.45" in str(exposed)


def test_visible_counterexamples_are_never_redacted():
    from app.api.plans_runs import _redact_held_out

    visible = _redact_held_out({
        "case_id": "case_001", "visibility": "visible", "exposed_to_model": False,
        "args": [[{"unit_price": "1.25"}]],
    })
    assert "1.25" in str(visible)
