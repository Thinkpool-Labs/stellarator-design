"""Bring a pull request's contribution into the trusted tree, as data only.

    python pr_gate.py <trusted dir> <pr dir> <data dir> <base sha> <head sha>

The workflow checks out the base branch (trusted: the checker, the records) and, separately, the pull
request's head. Nothing from the pull request is executed. This script lists what the pull request
changed against the base, refuses it unless every change is a new or edited JSON file directly inside
the pool's data directory, and copies those files into the trusted tree. The trusted checker then runs
on them. A pull request that edits the checker, the records, the tests or the workflow is refused
here, whatever its own copy of the workflow says, because this runs from the base branch.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

MAX_FILES = 20
MAX_BYTES = 1_000_000
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}\.json$")


def main(trusted: str, pr: str, data: str, base: str, head: str) -> int:
    out = subprocess.run(
        ["git", "-C", pr, "diff", "--name-status", "--no-renames", "-z", f"{base}...{head}"],
        capture_output=True, check=True,
    ).stdout.decode("utf-8", "replace")
    parts = [p for p in out.split("\0") if p]
    changes = list(zip(parts[0::2], parts[1::2]))
    problems, take = [], []
    for status, path in changes:
        folder, _, name = path.rpartition("/")
        if folder != data or not NAME.match(name):
            problems.append(f"{path}: only new JSON files directly in {data}/ are accepted")
        elif status != "A":
            problems.append(f"{path}: contributions add new files; changing or removing one is a maintainer's job")
        else:
            take.append(path)
    if not changes:
        problems.append("the pull request changes nothing")
    if len(take) > MAX_FILES:
        problems.append(f"at most {MAX_FILES} files per pull request")
    for path in take:
        src = Path(pr) / path
        if src.is_symlink() or not src.is_file():
            problems.append(f"{path}: not a regular file")
        elif src.stat().st_size > MAX_BYTES:
            problems.append(f"{path}: larger than {MAX_BYTES} bytes")
        else:
            try:
                json.loads(src.read_bytes().decode("utf-8"))
            except Exception as e:  # noqa: BLE001
                problems.append(f"{path}: not UTF-8 JSON ({e})")
    if problems:
        print(json.dumps({"gate": "refused", "problems": problems}))
        return 1
    for path in take:
        dst = Path(trusted) / path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(pr) / path, dst)
    print(json.dumps({"gate": "ok", "files": take}))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
