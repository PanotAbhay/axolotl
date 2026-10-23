"""Import safety - owner: Dev 3. Covers T-02.

An uploaded archive is hostile input. T-02: "Import malicious path-traversal ZIP ->
Rejected without writing outside extraction root."

The assertion that matters is not just "it raised" but **that nothing was written
outside the destination**, so each extraction test checks the filesystem afterwards.
"""

import zipfile

import pytest

from app.errors import AppError
from app.ingestion import _extract_zip, _write_folder
from app.ingestion.safety import (
    MAX_DEPTH,
    MAX_EXTRACTED_BYTES,
    MAX_FILES,
    UnsafeArchive,
    is_ignored,
    plan_extraction,
    plan_folder,
    safe_member_path,
)


def make_zip(path, members: dict[str, bytes], *, symlinks=()):
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
        for name, target in symlinks:
            info = zipfile.ZipInfo(name)
            info.external_attr = (0o120777 << 16)  # S_IFLNK
            archive.writestr(info, target)
    return path


# --------------------------------------------------------------------------
# T-02: path traversal
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    [
        "../escape.py",
        "../../etc/passwd",
        "pkg/../../escape.py",
        "/absolute.py",
        "/etc/passwd",
        "C:/Windows/evil.py",
        "C:\\Windows\\evil.py",
        "..\\windows\\evil.py",
    ],
)
def test_traversal_member_names_are_rejected(name):
    with pytest.raises(UnsafeArchive):
        safe_member_path(name)


def test_ordinary_names_are_accepted_and_normalised():
    assert safe_member_path("pkg/mod.py") == "pkg/mod.py"
    assert safe_member_path("./pkg/mod.py") == "pkg/mod.py"
    assert safe_member_path("pkg\\mod.py") == "pkg/mod.py"


def test_a_traversal_archive_is_rejected_and_writes_nothing(tmp_path):
    """The whole T-02 assertion: refused, and the filesystem is untouched."""
    archive = make_zip(tmp_path / "evil.zip", {
        "ok.py": b"x = 1\n",
        "../escaped.py": b"pwned = True\n",
    })
    destination = tmp_path / "snapshot"
    destination.mkdir()

    with pytest.raises(AppError) as caught:
        _extract_zip(archive, destination)

    assert caught.value.status_code == 422
    assert "rejected" in caught.value.message.lower()
    assert list(destination.rglob("*")) == [], "files were written despite rejection"
    assert not (tmp_path / "escaped.py").exists(), "a file escaped the destination"


def test_a_symlink_member_is_rejected(tmp_path):
    """A symlink can point anywhere, so it is refused rather than followed."""
    archive = make_zip(
        tmp_path / "link.zip", {"ok.py": b"x = 1\n"},
        symlinks=[("link.py", "/etc/passwd")],
    )
    with pytest.raises(UnsafeArchive, match="symlink"):
        with zipfile.ZipFile(archive) as opened:
            plan_extraction(opened)


def test_a_deeply_nested_path_is_rejected():
    deep = "/".join(["d"] * (MAX_DEPTH + 2)) + "/mod.py"
    with pytest.raises(UnsafeArchive, match="nested"):
        safe_member_path(deep)


# --------------------------------------------------------------------------
# limits
# --------------------------------------------------------------------------

def test_too_many_files_is_rejected(tmp_path):
    archive = make_zip(
        tmp_path / "many.zip",
        {f"m{i}.py": b"x = 1\n" for i in range(MAX_FILES + 5)},
    )
    with pytest.raises(UnsafeArchive, match="more than"):
        with zipfile.ZipFile(archive) as opened:
            plan_extraction(opened)


def test_an_archive_with_nothing_importable_is_rejected(tmp_path):
    archive = make_zip(tmp_path / "empty.zip", {"__pycache__/x.pyc": b"\x00"})
    with pytest.raises(UnsafeArchive, match="no importable files"):
        with zipfile.ZipFile(archive) as opened:
            plan_extraction(opened)


def test_a_decompression_bomb_is_rejected(tmp_path):
    archive = tmp_path / "bomb.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("bomb.txt", b"\0" * (8 * 1024 * 1024))
    with pytest.raises(UnsafeArchive):
        with zipfile.ZipFile(archive) as opened:
            plan_extraction(opened)


def test_a_valid_archive_extracts(tmp_path):
    archive = make_zip(tmp_path / "ok.zip", {
        "pkg/mod.py": b"x = 1\n",
        "pkg/__pycache__/mod.pyc": b"\x00",   # ignored
        "README.md": b"hello\n",
    })
    destination = tmp_path / "snapshot"
    destination.mkdir()

    copied = _extract_zip(archive, destination)

    assert "pkg/mod.py" in copied
    assert "README.md" in copied
    assert not any("__pycache__" in c for c in copied)
    assert (destination / "pkg" / "mod.py").read_text() == "x = 1\n"


def test_a_corrupt_archive_is_a_422_not_a_crash(tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"this is not a zip file")
    destination = tmp_path / "snapshot"
    destination.mkdir()

    with pytest.raises(AppError) as caught:
        _extract_zip(bad, destination)
    assert caught.value.status_code == 422


# --------------------------------------------------------------------------
# ignore rules
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path",
    [
        ".git/config", "node_modules/x/index.js", ".venv/lib/mod.py",
        "pkg/__pycache__/mod.pyc", ".env", "secrets/id_rsa",
        "assets/logo.png", "build/out.so", "keys/server.pem",
    ],
)
def test_noise_and_secrets_are_ignored(path):
    assert is_ignored(path) is True


@pytest.mark.parametrize(
    "path", ["pricing.py", "pkg/orders.py", "tests/test_baseline.py", "README.md"]
)
def test_real_source_is_not_ignored(path):
    assert is_ignored(path) is False


# --------------------------------------------------------------------------
# folder uploads: the same rules, applied to paths sent by the browser
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "path", ["../evil.py", "/etc/passwd", "C:/Windows/evil.py", "pkg/../../evil.py"]
)
def test_a_dangerous_folder_path_rejects_the_upload_and_writes_nothing(tmp_path, path):
    destination = tmp_path / "snapshot"
    destination.mkdir()
    folder = [("ok.py", b"x = 1\n"), (path, b"pwned = True\n")]

    with pytest.raises(AppError) as caught:
        _write_folder(folder, destination)

    assert caught.value.status_code == 422
    assert list(tmp_path.rglob("*.py")) == []


def test_a_folder_upload_writes_its_files_and_drops_noise(tmp_path):
    folder = [
        ("setup.py", b"setup()\n"),
        ("pkg/mod.py", b"def f():\n    return 1\n"),
        (".env", b"SECRET=1\n"),
        ("pkg/__pycache__/mod.cpython-312.pyc", b"\x00"),
    ]

    copied = _write_folder(folder, tmp_path)

    assert copied == ["setup.py", "pkg/mod.py"]
    assert (tmp_path / "pkg" / "mod.py").read_bytes() == b"def f():\n    return 1\n"
    assert not (tmp_path / ".env").exists()


def test_a_duplicate_folder_path_is_rejected_whatever_its_case():
    with pytest.raises(UnsafeArchive, match="duplicate"):
        plan_folder([("pkg/Mod.py", 1), ("pkg/mod.py", 1)])


def test_too_many_folder_files_is_rejected():
    with pytest.raises(UnsafeArchive, match="more than"):
        plan_folder([(f"m{i}.py", 1) for i in range(MAX_FILES + 1)])


def test_an_oversized_folder_is_rejected():
    with pytest.raises(UnsafeArchive, match="larger than"):
        plan_folder([("a.py", MAX_EXTRACTED_BYTES), ("b.py", 1)])


def test_a_folder_with_nothing_importable_is_rejected():
    with pytest.raises(UnsafeArchive, match="no importable files"):
        plan_folder([(".env", 10), ("logo.png", 10)])
