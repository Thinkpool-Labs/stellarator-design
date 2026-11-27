"""Refuse a tree that carries anything Python could import or execute besides the checker.

Called first by check_all.py. The check runs with `python -I` (no PYTHONPATH, no user site, no script
directory on sys.path) in an image whose dependencies live outside /work, so none of these files could
run anyway. This is the second line: a contribution is data in one directory, and anything else in
the tree that looks like code or a path hook means the tree is not the one the host shared. The
attempts log (attempts/, work that set no record) is data too: JSON files only, small.
"""
from __future__ import annotations

from pathlib import Path

CODE_DIRS = {"checker", "tests", "baselines", ".github"}
SUFFIXES = {".py", ".pth", ".pyc", ".so", ".pyd"}
MAX_BYTES = 1_000_000
ATTEMPT_BYTES = 64_000


def problems(root: Path, data_dir: str) -> list[str]:
    out = []
    for p in root.rglob("*"):
        rel = p.relative_to(root)
        top = rel.parts[0]
        if top in {".git", "__pycache__", ".pytest_cache"} or "__pycache__" in rel.parts:
            continue
        if p.is_symlink():
            out.append(f"{rel}: symlinks are not accepted")
        elif top == ".deps" or p.name in {"sitecustomize.py", "usercustomize.py"}:
            out.append(f"{rel}: not part of the pool")
        elif p.suffix in SUFFIXES and top not in CODE_DIRS:
            out.append(f"{rel}: code outside the checker")
        elif top == "attempts" and p.is_file():
            if len(rel.parts) != 2 or (p.suffix != ".json" and p.name != "README.md"):
                out.append(f"{rel}: only JSON files directly in attempts/")
            elif p.stat().st_size > ATTEMPT_BYTES:
                out.append(f"{rel}: larger than {ATTEMPT_BYTES} bytes")
        elif top == data_dir and p.is_file():
            if p.suffix != ".json" or len(rel.parts) != 2:
                out.append(f"{rel}: only JSON files directly in {data_dir}/")
            elif p.stat().st_size > MAX_BYTES:
                out.append(f"{rel}: larger than {MAX_BYTES} bytes")
    return out
