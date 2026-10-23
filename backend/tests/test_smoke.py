"""Smoke tests - owner: Dev 2. The Fri 18:00 gate: the app boots and /system/status is real.

These must pass with NO .env and no Atlas reachable: the app boots and honestly reports
dependencies as unavailable. They must never assert that a dependency is ok.
"""

from fastapi.testclient import TestClient

from tests.conftest import API


def test_app_imports_and_boots(client: TestClient) -> None:
    assert client.app is not None


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get(f"{API}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_system_status_returns_json_in_contract_shape(client: TestClient) -> None:
    """SHARED_CONTRACTS §6: {mongodb, search_indexes:{keyword,vector},
    runner:{mode,available}, gemini:{model,reachable}}."""
    response = client.get(f"{API}/system/status")
    assert response.status_code == 200

    body = response.json()
    assert set(body) >= {"mongodb", "search_indexes", "runner", "gemini"}

    assert body["mongodb"] in {"ok", "unavailable"}
    assert set(body["search_indexes"]) == {"keyword", "vector"}
    for value in body["search_indexes"].values():
        assert value in {"ok", "unavailable", "building"}

    assert set(body["runner"]) == {"mode", "available"}
    assert body["runner"]["mode"] in {"trusted_docker", "disabled"}
    assert isinstance(body["runner"]["available"], bool)

    assert set(body["gemini"]) == {"model", "reachable"}
    assert isinstance(body["gemini"]["model"], str) and body["gemini"]["model"]
    assert isinstance(body["gemini"]["reachable"], bool)


def test_contracts_module_imports() -> None:
    """§4 models must import cleanly - everyone depends on this file."""
    from app.models import contracts

    assert contracts.RepositoryRecord.model_fields["repository_id"].is_required()
    assert "modern_python3" not in contracts.PlanStatus.__args__  # sanity: enums are distinct


def test_error_envelope_shape(client: TestClient) -> None:
    """§6: errors are {"error": {"code", "message", "details"}}."""
    response = client.get(f"{API}/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == "NOT_FOUND"
