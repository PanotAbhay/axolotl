"""Build the UI upload ZIP from the current chess source, excluding caches."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parent
source = root / "chess"
output = root / "chess-input.zip"
with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
    for path in sorted(source.rglob("*")):
        if (
            path.is_file()
            and not path.is_symlink()
            and path.suffix in {".py", ".md"}
            and "__pycache__" not in path.parts
        ):
            archive.write(path, path.relative_to(source).as_posix())
print(output)
