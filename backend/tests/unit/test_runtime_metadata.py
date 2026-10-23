"""Uploaded metadata must be read statically and never mistaken for runtime proof."""

from pathlib import Path

from app.ingestion.runtime import inspect_runtime


def test_chess_declares_python27():
    root = Path(__file__).resolve().parents[3] / "demo" / "chess"
    result = inspect_runtime(root)
    assert result["declared_python"] == "2.7"
    assert result["runtime_verified"] is False
    assert result["evidence"] == ["setup.py: >=2.7,<3"]


def test_setup_is_not_executed(tmp_path):
    (tmp_path / "setup.py").write_text(
        "raise RuntimeError('must never execute')\nsetup(python_requires='>=2.7,<3')\n"
    )
    assert inspect_runtime(tmp_path)["declared_python"] == "2.7"


def test_unknown_and_conflicting_metadata(tmp_path):
    assert inspect_runtime(tmp_path)["declared_python"] is None
    (tmp_path / "setup.py").write_text("setup(python_requires='>=2.7,<3')")
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python=">=3.10"\n')
    assert inspect_runtime(tmp_path)["declared_python"] is None


def test_single_directory_archive_and_invalid_file(tmp_path):
    child = tmp_path / "local-chess"
    child.mkdir()
    (child / "setup.py").write_text("setup(python_requires='>=2.7,<3')")
    assert inspect_runtime(tmp_path)["declared_python"] == "2.7"
    (child / "setup.py").write_text("not valid python !")
    assert inspect_runtime(tmp_path)["declared_python"] is None


def test_python3_is_not_labelled_python2(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python=">=3.10"\n')
    assert inspect_runtime(tmp_path)["declared_python"] == ">=3.10"


async def test_runtime_endpoint_reads_only_registered_snapshot(client, monkeypatch, tmp_path):
    from app import ingestion

    requested = []

    async def repository(repo_id):
        requested.append(repo_id)
        return object()

    monkeypatch.setattr(ingestion, "get_repository", repository)
    monkeypatch.setattr(ingestion, "snapshot_path", lambda repo_id: tmp_path)
    (tmp_path / "setup.py").write_text("setup(python_requires='>=2.7,<3')")
    response = client.get("/api/v1/repositories/repo_runtime/runtime")
    assert response.status_code == 200
    assert response.json()["declared_python"] == "2.7"
    assert response.json()["runtime_verified"] is False
    assert requested == ["repo_runtime"]
