"""Read declared Python requirements without importing uploaded setup.py."""

import ast
import re
import tomllib
from pathlib import Path


def inspect_runtime(root: Path) -> dict:
    evidence = []
    requirements = []
    # Also accept archives containing a single top-level project directory.
    roots = [root]
    children = [p for p in root.iterdir() if p.is_dir() and not p.is_symlink()]
    if len(children) == 1:
        roots.append(children[0])
    for base in roots:
        for name in ("setup.py", "pyproject.toml"):
            path = base / name
            if not path.is_file() or path.is_symlink() or path.stat().st_size > 65536:
                continue
            try:
                text = path.read_text(encoding="utf-8")
                if name == "pyproject.toml":
                    requirement = tomllib.loads(text).get("project", {}).get("requires-python")
                    values = [requirement] if isinstance(requirement, str) else []
                else:
                    tree = ast.parse(text)
                    values = [
                        kw.value.value
                        for node in ast.walk(tree)
                        if isinstance(node, ast.Call)
                        for kw in node.keywords
                        if kw.arg == "python_requires"
                        and isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, str)
                    ]
                for requirement in values:
                    requirements.append(requirement)
                    evidence.append(f"{path.relative_to(root).as_posix()}: {requirement}")
            except (ValueError, SyntaxError, UnicodeError, OSError):
                continue
    unique = list(dict.fromkeys(requirements))
    declared = None
    if len(unique) == 1:
        # Only label an exact legacy family when metadata excludes Python 3.
        req = unique[0].replace(" ", "")
        if re.search(r"(?:>=|==|~=)2\.7(?:[,.*]|$)", req) and (
            re.search(r"<3(?:\.0)?(?:,|$)", req) or req.startswith("==2.7")
        ):
            declared = "2.7"
        else:
            declared = req
    return {
        "declared_python": declared,
        "evidence": evidence,
        "runtime_verified": False,
        "note": "Read from package metadata; no uploaded code was executed.",
    }
