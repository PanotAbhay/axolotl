"""Shared test fixtures.

Each dev tests their own package under tests/{unit,integration,security}.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app

API = "/api/v1"


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """TestClient inside a context manager so the lifespan hook runs (opens/closes Mongo)."""
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def offline_import(request: pytest.FixtureRequest,
                   monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep import off the network unless a test is marked `live`.

    Two things in the import path reach outside otherwise:

    - **Enrichment** is one `generate_content` plus one `embed_content` per chunk.
      The import tests import the fixture eleven times, so leaving it on would mean
      roughly five hundred model calls per run on a machine with a key - slow, and
      it charges quota for tests that are not about search at all.
    - **Waiting for the chunks to become searchable** polls Atlas for up to 45
      seconds. Tests stub chunk persistence, so there is nothing to wait for and the
      whole timeout would elapse eleven times over.

    Chunk *building* still happens, so the chunking side stays covered.
    """
    settings = get_settings()
    original = settings.index_on_import

    if not request.node.get_closest_marker("live"):
        settings.index_on_import = False

        from app.search import pipeline

        async def already_searchable(repository_id: str, **_: object) -> bool:
            return True

        monkeypatch.setattr(pipeline, "wait_until_searchable", already_searchable)
    try:
        yield
    finally:
        settings.index_on_import = original
