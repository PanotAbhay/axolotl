"""The search endpoint - owner: Dev 3. SHARED_CONTRACTS §6. Offline.

The search layer itself is stubbed here; what is under test is the endpoint contract
the frontend codes against: the response shape, and the three ways a request can be
wrong. Each of those must arrive as a §6 error envelope with the right status, because
a UI that cannot tell "no matches" from "unknown repository" from "index still
building" will show the user the wrong thing in two cases out of three.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.errors import AppError
from app.main import create_app
from app.models.contracts import RepositoryRecord, SearchHit
from tests.conftest import API

REPO = "repo_000000000001"


def a_hit(**extra: Any) -> SearchHit:
    fields: dict[str, Any] = {
        "chunk_id": "chunk_abc",
        "symbol_id": "sym_abc",
        "module_id": "pricing",
        "path": "pricing.py",
        "start_line": 48,
        "end_line": 104,
        "snapshot_hash": "sha256:abc",
        "snippet": "def finalise_amount(lines, category):",
        "description": "Works out what a customer finally owes.",
        "match_method": "hybrid",
        "score": 0.0328,
        "rank": 1,
        "keyword_rank": 1,
        "vector_rank": 1,
        "qualified_name": "pricing.finalise_amount",
        "kind": "function",
    }
    fields.update(extra)
    return SearchHit(**fields)


@pytest.fixture
def api(monkeypatch):
    """A client whose repository lookup and search are both stubbed."""
    state: dict[str, Any] = {
        "repository": REPO,
        "result": {"mode_used": "hybrid", "native_hybrid": True, "hits": [a_hit()]},
        "raises": None,
        "calls": [],
    }

    async def get_repository(repo_id: str) -> RepositoryRecord:
        if repo_id != state["repository"]:
            raise AppError("NOT_FOUND", f"Unknown repository {repo_id}", 404)
        return RepositoryRecord(
            repository_id=repo_id, name="legacy_orders",
            snapshot_hash="sha256:abc", origin="demo_fixture", executable=True,
            demo_fixture_id="legacy_orders", file_count=10, module_count=7,
            symbol_count=40, test_file_count=1, analysis_status="ok",
            created_at=datetime.now(UTC),
        )

    async def search_repository(repo_id, query, mode="hybrid", limit=8):
        state["calls"].append({"repo_id": repo_id, "query": query,
                               "mode": mode, "limit": limit})
        if state["raises"] is not None:
            raise state["raises"]
        return state["result"]

    from app.api import search as search_api

    monkeypatch.setattr(search_api.graphstore, "get_repository", get_repository)
    monkeypatch.setattr(search_api.search, "search_repository", search_repository)

    with TestClient(create_app()) as client:
        yield client, state


def test_a_search_returns_the_mode_that_ran_and_the_hits(api):
    client, _ = api
    response = client.get(f"{API}/repositories/{REPO}/search", params={"q": "rounding"})

    assert response.status_code == 200
    body = response.json()
    assert body["mode_used"] == "hybrid"
    assert body["native_hybrid"] is True

    hit = body["hits"][0]
    assert hit["qualified_name"] == "pricing.finalise_amount"
    assert hit["path"] == "pricing.py"
    assert (hit["start_line"], hit["end_line"]) == (48, 104)
    assert hit["keyword_rank"] == 1 and hit["vector_rank"] == 1
    # 768 floats per hit would dwarf the payload and help nobody.
    assert "embedding" not in hit


def test_hybrid_is_the_default_mode(api):
    client, state = api
    client.get(f"{API}/repositories/{REPO}/search", params={"q": "rounding"})
    assert state["calls"][-1]["mode"] == "hybrid"


def test_the_mode_and_limit_are_passed_through(api):
    client, state = api
    client.get(f"{API}/repositories/{REPO}/search",
               params={"q": "rounding", "mode": "vector", "limit": 3})
    assert state["calls"][-1]["mode"] == "vector"
    assert state["calls"][-1]["limit"] == 3


def test_an_unknown_repository_is_a_404_not_an_empty_result(api):
    """Zero hits would send the caller hunting for a problem with their query."""
    client, _ = api
    response = client.get(f"{API}/repositories/repo_nope/search",
                          params={"q": "rounding"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_the_repository_is_checked_before_the_search_runs(api):
    client, state = api
    client.get(f"{API}/repositories/repo_nope/search", params={"q": "rounding"})
    assert state["calls"] == []


def test_an_unknown_mode_is_rejected(api):
    client, _ = api
    response = client.get(f"{API}/repositories/{REPO}/search",
                          params={"q": "rounding", "mode": "magic"})
    assert response.status_code == 422


def test_a_missing_or_empty_query_is_rejected(api):
    client, _ = api
    assert client.get(f"{API}/repositories/{REPO}/search").status_code == 422
    assert client.get(f"{API}/repositories/{REPO}/search",
                      params={"q": ""}).status_code == 422


def test_an_absurdly_long_query_is_rejected(api):
    client, state = api
    response = client.get(f"{API}/repositories/{REPO}/search",
                          params={"q": "x" * 501})
    assert response.status_code == 422
    assert state["calls"] == []


def test_a_limit_outside_the_range_is_rejected(api):
    client, _ = api
    for limit in (0, 51):
        response = client.get(f"{API}/repositories/{REPO}/search",
                              params={"q": "rounding", "limit": limit})
        assert response.status_code == 422


def test_an_index_that_is_not_ready_is_a_503_with_its_own_code(api):
    """§6: the UI must be able to say "still building", not "nothing found"."""
    client, state = api
    state["raises"] = AppError(
        "SEARCH_INDEX_NOT_READY", "The keyword index is still building.",
        status_code=503, details={"index": "keyword", "state": "building"},
    )
    response = client.get(f"{API}/repositories/{REPO}/search",
                          params={"q": "rounding"})

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "SEARCH_INDEX_NOT_READY"
    assert error["details"]["state"] == "building"


def test_an_honest_empty_result_is_a_200(api):
    """Nothing matched is a successful answer, and must not look like a failure."""
    client, state = api
    state["result"] = {"mode_used": "hybrid", "native_hybrid": True, "hits": []}
    response = client.get(f"{API}/repositories/{REPO}/search",
                          params={"q": "nothing matches this"})

    assert response.status_code == 200
    assert response.json()["hits"] == []
