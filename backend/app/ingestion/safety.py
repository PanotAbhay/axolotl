"""Import safety - owner: Dev 3. Spec §5.1, covers T-02.

Uploaded archives are hostile input. Nothing here executes anything; the job is to
decide which members may be written to disk at all, and to refuse the archive outright
when it looks like an attack rather than a mistake.

Limits are from the Dev 3 brief: 10 MB compressed, 50 MB extracted, 500 files,
depth 12.
"""

from __future__ import annotations

import stat
import zipfile
from pathlib import PurePosixPath

MAX_ARCHIVE_BYTES = 10 * 1024 * 1024       # compressed
MAX_EXTRACTED_BYTES = 50 * 1024 * 1024     # uncompressed, summed
MAX_FILES = 500
MAX_DEPTH = 12
MAX_COMPRESSION_RATIO = 100                # a single member; bomb heuristic

# Never copied into a snapshot: noise, build output, or secrets.
IGNORED_DIRECTORIES = frozenset({
    ".git", ".hg", ".svn", "__pycache__", "node_modules", ".venv", "venv",
    "env", ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist",
    "build", ".idea", ".vscode", ".eggs", "site-packages",
})
IGNORED_FILENAMES = frozenset({
    ".env", ".env.local", ".DS_Store", "Thumbs.db", "id_rsa", "id_ed25519",
})
IGNORED_SUFFIXES = frozenset({
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin", ".zip", ".tar",
    ".gz", ".whl", ".jpg", ".jpeg", ".png", ".gif", ".pdf", ".mp4", ".sqlite",
    ".db", ".pem", ".key", ".p12", ".pfx",
})


class UnsafeArchive(Exception):
    """The archive is rejected outright. The message is shown to the user."""


def is_ignored(relative_path: str) -> bool:
    """True for paths that never reach a snapshot."""
    path = PurePosixPath(str(relative_path).replace("\\", "/"))
    if any(part in IGNORED_DIRECTORIES for part in path.parts[:-1]):
        return True
    if path.name in IGNORED_FILENAMES:
        return True
    if path.suffix.lower() in IGNORED_SUFFIXES:
        return True
    # Hidden files are skipped, but not hidden directories already handled above.
    return path.name.startswith(".") and path.suffix != ""


def safe_member_path(name: str) -> str:
    """Normalise an archive member name, or raise UnsafeArchive.

    This is the T-02 guard. Rejects, in order: absolute paths, Windows drive
    letters, any `..` component, and empty results. Returns a clean relative
    POSIX path.
    """
    raw = str(name).replace("\\", "/")

    if raw.startswith("/"):
        raise UnsafeArchive(f"absolute path in archive: {name!r}")
    if len(raw) >= 2 and raw[1] == ":":
        raise UnsafeArchive(f"drive-letter path in archive: {name!r}")

    path = PurePosixPath(raw)
    if any(part == ".." for part in path.parts):
        raise UnsafeArchive(f"parent-directory traversal in archive: {name!r}")
    if path.is_absolute():
        raise UnsafeArchive(f"absolute path in archive: {name!r}")

    cleaned = "/".join(part for part in path.parts if part not in {"", "."})
    if not cleaned:
        raise UnsafeArchive(f"empty member name in archive: {name!r}")
    if len(PurePosixPath(cleaned).parts) > MAX_DEPTH:
        raise UnsafeArchive(
            f"path nested deeper than {MAX_DEPTH}: {name!r}"
        )
    return cleaned


def is_symlink(info: zipfile.ZipInfo) -> bool:
    """ZIP stores the unix mode in the top 16 bits of external_attr."""
    return stat.S_ISLNK(info.external_attr >> 16)


def plan_extraction(archive: zipfile.ZipFile) -> list[tuple[zipfile.ZipInfo, str]]:
    """Decide what may be written, or raise UnsafeArchive.

    Returns (member, clean relative path) pairs. Directories, ignored paths and
    zero-byte entries are dropped silently; anything dangerous raises, because a
    traversal attempt is not a file we should quietly skip - it is a signal the
    whole archive is hostile.
    """
    accepted: list[tuple[zipfile.ZipInfo, str]] = []
    total_uncompressed = 0

    for info in archive.infolist():
        if is_symlink(info):
            raise UnsafeArchive(f"symlink in archive: {info.filename!r}")

        relative = safe_member_path(info.filename)

        if info.is_dir():
            continue

        # Decompression bomb: a tiny member claiming an enormous expansion.
        if info.compress_size > 0:
            ratio = info.file_size / info.compress_size
            if ratio > MAX_COMPRESSION_RATIO and info.file_size > 1024 * 1024:
                raise UnsafeArchive(
                    f"suspicious compression ratio ({ratio:.0f}x) for {info.filename!r}"
                )

        total_uncompressed += info.file_size
        if total_uncompressed > MAX_EXTRACTED_BYTES:
            raise UnsafeArchive(
                f"archive expands beyond {MAX_EXTRACTED_BYTES // (1024 * 1024)} MB"
            )

        if is_ignored(relative):
            continue

        accepted.append((info, relative))
        if len(accepted) > MAX_FILES:
            raise UnsafeArchive(f"archive holds more than {MAX_FILES} files")

    if not accepted:
        raise UnsafeArchive("archive contains no importable files")
    return accepted


def plan_folder(entries: list[tuple[str, int]]) -> list[tuple[int, str]]:
    """Decide which files of a folder upload may be written, or raise UnsafeArchive.

    `entries` are (path inside the folder, size in bytes) in upload order. The rules
    are `plan_extraction`'s: a dangerous path rejects the whole upload, ignored paths
    are dropped. Returns (entry index, clean relative path) pairs.
    """
    accepted: list[tuple[int, str]] = []
    seen: set[str] = set()
    total = 0

    for index, (name, size) in enumerate(entries):
        relative = safe_member_path(name)

        # Case-folded, because on Windows `A.py` and `a.py` are one file and the
        # second write would silently replace the first.
        if relative.casefold() in seen:
            raise UnsafeArchive(f"duplicate path in upload: {name!r}")
        seen.add(relative.casefold())

        total += size
        if total > MAX_EXTRACTED_BYTES:
            raise UnsafeArchive(
                f"upload is larger than {MAX_EXTRACTED_BYTES // (1024 * 1024)} MB"
            )

        if is_ignored(relative):
            continue

        accepted.append((index, relative))
        if len(accepted) > MAX_FILES:
            raise UnsafeArchive(f"upload holds more than {MAX_FILES} files")

    if not accepted:
        raise UnsafeArchive("upload contains no importable files")
    return accepted
