"""Migration target tests - owner: Dev 2. Covers T-08 (unsupported target rejected)."""

import pytest
from fastapi.testclient import TestClient

from app.api.targets import MIGRATION_TARGETS, require_supported_target
from app.errors import AppError
from tests.conftest import API


def test_only_modern_python3_is_supported():
    supported = [t.target_id for t in MIGRATION_TARGETS if t.supported]
    assert supported == ["modern_python3"]


def test_every_unsupported_target_explains_itself():
    """The UI shows these disabled with a reason, so the reason must exist."""
    for target in MIGRATION_TARGETS:
        if not target.supported:
            assert target.unsupported_reason, target.target_id


def test_endpoint_lists_every_target(client: TestClient):
    response = client.get(f"{API}/migration-targets")
    assert response.status_code == 200

    body = response.json()
    assert {t["target_id"] for t in body} == {
        "modern_python3", "fastapi", "async_python",
        "python_to_typescript", "python2_to_3",
    }
    assert set(body[0]) == {
        "target_id", "label", "supported", "description", "unsupported_reason",
    }


def test_supported_target_resolves():
    assert require_supported_target("modern_python3").target_id == "modern_python3"


@pytest.mark.parametrize(
    "target_id",
    ["fastapi", "async_python", "python_to_typescript", "python2_to_3"],
)
def test_unsupported_target_is_rejected_with_422(target_id):
    """T-08: disabled or rejected at the backend with a clear error."""
    with pytest.raises(AppError) as caught:
        require_supported_target(target_id)

    error = caught.value
    assert error.code == "UNSUPPORTED_TARGET"
    assert error.status_code == 422
    assert error.details["target_id"] == target_id
    assert error.details["reason"]


def test_unknown_target_is_rejected_the_same_way():
    with pytest.raises(AppError) as caught:
        require_supported_target("cobol_to_rust")
    assert caught.value.code == "UNSUPPORTED_TARGET"
    assert caught.value.status_code == 422
