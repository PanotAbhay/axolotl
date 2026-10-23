"""Artefact tests - owner: Dev 2. Covers T-16.

T-16 is "the source diff matches the verified workspace artefact". The failure it
guards against is subtle: a diff that looks plausible but is not the diff of the
revision the verifier actually passed. These tests make that case fail loudly.
"""

import pytest

from app.models.contracts import RunSummary, UnitRunState
from app.orchestration import ports as ports_module
from app.orchestration import store as store_module
from app.reports import artefacts
from app.reports.artefacts import (
    render_unified_diff,
    sha256_bytes,
    verify_patch_matches_revision,
)

REVISION = "rev_abc123abc123"

DIFF_A = {
    "path": "pricing.py",
    "unified_diff": "--- a/pricing.py\n+++ b/pricing.py\n@@\n-old\n+new\n",
}
DIFF_B = {
    "path": "orders.py",
    "unified_diff": "--- a/orders.py\n+++ b/orders.py\n@@\n-x\n+y\n",
}


def make_run() -> RunSummary:
    now = store_module.utcnow()
    return RunSummary(
        run_id="run_000000000001",
        plan_id="plan_000000000001",
        repository_id="repo_000000000001",
        state="completed",
        current_unit=None,
        units=[UnitRunState(unit_id="unit_pricing", module_ids=["module_pricing"],
                            status="passed")],
        units_total=1, units_verified=1, units_blocked=0,
        tests_passed=10, tests_failed=0, tests_inconclusive=0,
        last_event_sequence=20, model="gemini-4-argon",
        runner_mode="trusted_docker", created_at=now, updated_at=now,
    )


@pytest.fixture
def artefact_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(artefacts, "artefact_root", lambda run_id: tmp_path)
    return tmp_path


@pytest.fixture
def recorded(monkeypatch):
    """Capture artefacts instead of writing them to Atlas."""
    saved: list[dict] = []

    async def save_artefact(artefact):
        saved.append(artefact)
        return artefact

    async def list_artefacts(run_id):
        return [a for a in saved if a["run_id"] == run_id]

    monkeypatch.setattr(store_module, "save_artefact", save_artefact)
    monkeypatch.setattr(store_module, "list_artefacts", list_artefacts)
    return saved


def set_diff(monkeypatch, files):
    async def diff(run_id, base, revision, paths=None):
        return files

    monkeypatch.setattr(ports_module, "diff", diff)


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def test_a_diff_renders_the_same_way_every_time():
    """T-16 compares hashes, so rendering must not depend on dict ordering."""
    assert render_unified_diff([DIFF_A, DIFF_B]) == render_unified_diff([DIFF_B, DIFF_A])


def test_files_are_rendered_in_path_order():
    rendered = render_unified_diff([DIFF_A, DIFF_B])
    assert rendered.index("orders.py") < rendered.index("pricing.py")


def test_an_empty_diff_renders_empty():
    assert render_unified_diff([]) == ""


def test_entries_without_a_diff_are_skipped():
    assert render_unified_diff([{"path": "a.py"}]) == ""


# --------------------------------------------------------------------------
# writing
# --------------------------------------------------------------------------

async def test_a_patch_artefact_records_its_hash_and_changed_files(
    artefact_dir, recorded, monkeypatch
):
    set_diff(monkeypatch, [DIFF_A, DIFF_B])
    artefact = await artefacts.write_patch_artefact(make_run(), REVISION)

    assert artefact is not None
    assert artefact["kind"] == "patch"
    assert artefact["revision"] == REVISION
    assert artefact["changed_files"] == ["orders.py", "pricing.py"]
    assert artefact["sha256"] == sha256_bytes(
        render_unified_diff([DIFF_A, DIFF_B]).encode("utf-8")
    )
    assert (artefact_dir / "migration.patch").is_file()


async def test_no_patch_artefact_when_the_verifier_is_not_wired_up(
    artefact_dir, recorded, monkeypatch
):
    async def unavailable(*args, **kwargs):
        raise ports_module.IntegrationUnavailable("Dev 4", "app.sandbox", "diff")

    monkeypatch.setattr(ports_module, "diff", unavailable)
    assert await artefacts.write_patch_artefact(make_run(), REVISION) is None
    assert recorded == []


async def test_no_archive_artefact_without_an_accepted_tree(artefact_dir, recorded):
    assert await artefacts.write_archive_artefact(make_run(), None) is None


async def test_an_archive_is_written_from_an_accepted_tree(
    artefact_dir, recorded, tmp_path
):
    tree = tmp_path / "accepted"
    (tree / "pkg").mkdir(parents=True)
    (tree / "pkg" / "pricing.py").write_text("x = 1\n", encoding="utf-8")
    (tree / "pkg" / "__pycache__").mkdir()
    (tree / "pkg" / "__pycache__" / "junk.pyc").write_bytes(b"\x00")

    artefact = await artefacts.write_archive_artefact(make_run(), tree)

    assert artefact is not None
    assert artefact["kind"] == "archive"

    import zipfile

    with zipfile.ZipFile(artefact["path"]) as archive:
        names = archive.namelist()
    assert "pkg/pricing.py" in names
    assert not any("__pycache__" in n for n in names)


# --------------------------------------------------------------------------
# T-16
# --------------------------------------------------------------------------

async def test_a_patch_matching_its_revision_passes(artefact_dir, recorded, monkeypatch):
    set_diff(monkeypatch, [DIFF_A])
    await artefacts.write_patch_artefact(make_run(), REVISION)

    verdict = await verify_patch_matches_revision("run_000000000001", REVISION)

    assert verdict["checked"] is True
    assert verdict["matches"] is True
    assert verdict["stored_sha256"] == verdict["recomputed_sha256"]


async def test_a_patch_whose_content_drifted_is_caught(
    artefact_dir, recorded, monkeypatch
):
    """The exact T-16 failure: the stored diff is not the verified revision's diff."""
    set_diff(monkeypatch, [DIFF_A])
    await artefacts.write_patch_artefact(make_run(), REVISION)

    set_diff(monkeypatch, [DIFF_A, DIFF_B])  # workspace moved on
    verdict = await verify_patch_matches_revision("run_000000000001", REVISION)

    assert verdict["checked"] is True
    assert verdict["matches"] is False
    assert verdict["stored_sha256"] != verdict["recomputed_sha256"]
    assert "does not match" in verdict["reason"]


async def test_a_patch_recorded_for_another_revision_is_caught(
    artefact_dir, recorded, monkeypatch
):
    set_diff(monkeypatch, [DIFF_A])
    await artefacts.write_patch_artefact(make_run(), "rev_000000000old")

    verdict = await verify_patch_matches_revision("run_000000000001", REVISION)

    assert verdict["matches"] is False
    assert "rev_000000000old" in verdict["reason"]


async def test_nothing_to_check_when_no_patch_was_recorded(artefact_dir, recorded):
    verdict = await verify_patch_matches_revision("run_000000000001", REVISION)
    assert verdict["checked"] is False
    assert "no patch artefact" in verdict["reason"]


async def test_the_check_is_skipped_not_passed_when_diff_is_unavailable(
    artefact_dir, recorded, monkeypatch
):
    """An unavailable verifier must never read as a clean T-16 result."""
    set_diff(monkeypatch, [DIFF_A])
    await artefacts.write_patch_artefact(make_run(), REVISION)

    async def unavailable(*args, **kwargs):
        raise ports_module.IntegrationUnavailable("Dev 4", "app.sandbox", "diff")

    monkeypatch.setattr(ports_module, "diff", unavailable)
    verdict = await verify_patch_matches_revision("run_000000000001", REVISION)

    assert verdict["checked"] is False
    assert verdict.get("matches") is None
