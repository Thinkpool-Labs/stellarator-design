"""The attempts log's checker, and how it sits beside the record check. Run: python -m pytest tests -q"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "checker"))

from attempts_check import judge  # noqa: E402
from hygiene import problems  # noqa: E402

POOL = "stellarator-design"
GOOD = {
    "schema": "thinkpool-attempt/1",
    "pool": POOL,
    "author": "octocat",
    "date": "2026-11-27",
    "target": "simple_to_build above 0.6956",
    "approach": "What was tried, in enough detail to repeat it.\nSecond line.",
    "best_value": "0.62 (feasible, below the record)",
    "outcome": "no_improvement",
    "why": "Where it stalled, and the guess why.",
    "compute": {"hours": 6.5, "hardware": "laptop, 8 cores"},
    "artifact": {"url": "https://github.com/octocat/try/blob/0123abc/search.py", "path": "search.py",
                 "sha256": "0" * 64},
    "references": ["https://arxiv.org/abs/1407.4897"],
    "tags": ["local-search"],
}


def test_good_attempt():
    assert judge(copy.deepcopy(GOOD), POOL)["verdict"] == "VALID"
    short = {k: v for k, v in GOOD.items() if k not in {"best_value", "references", "tags"}}
    short["artifact"] = {"url": "https://gist.github.com/octocat/abcdef0123"}
    assert judge(short, POOL)["verdict"] == "VALID"


@pytest.mark.parametrize("change", [
    {"pool": "another-pool"},
    {"author": "@octocat"},
    {"date": "2099-01-01"},
    {"date": "27/11/2026"},
    {"outcome": "record"},
    {"target": "two\nlines"},
    {"approach": "hidden " + chr(0x202E) + "override"},
    {"why": "bell" + chr(7)},
    {"compute": {"hours": True}},
    {"compute": {"hours": -1}},
    {"compute": {"hours": 1, "cost": "9"}},
    {"artifact": {"url": "https://evil.example/x"}},
    {"artifact": {"url": "javascript:alert(1)"}},
    {"artifact": {"url": "https://github.com/a/b", "path": "../x", "sha256": "0" * 64}},
    {"artifact": {"url": "https://github.com/a/b", "path": "x", "sha256": "XYZ"}},
    {"references": ["http://arxiv.org/abs/1"]},
    {"tags": ["Not A Slug"]},
    {"extra": 1},
    {"target": "x" * 201},
])
def test_refusals(change):
    bad = copy.deepcopy(GOOD)
    bad.update(change)
    with pytest.raises(ValueError):
        judge(bad, POOL)


def test_hygiene_takes_attempts_as_data_only(tmp_path):
    root = tmp_path / "pool"
    (root / "attempts" / "sub").mkdir(parents=True)
    (root / "attempts" / "ok.json").write_text(json.dumps(GOOD))
    (root / "attempts" / "README.md").write_text("x")
    assert problems(root, "designs") == []
    (root / "attempts" / "notes.txt").write_text("x")
    (root / "attempts" / "sub" / "deep.json").write_text("{}")
    (root / "attempts" / "run.py").write_text("print(1)")
    found = " ".join(problems(root, "designs"))
    assert "notes.txt" in found and "deep.json" in found and "run.py" in found


def test_an_attempt_never_passes_the_record_check(tmp_path):
    copy_ = tmp_path / "pool"
    shutil.copytree(ROOT, copy_, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    (copy_ / "attempts" / "2026-11-27-octocat.json").write_text(json.dumps(GOOD))
    r = subprocess.run([sys.executable, "-I", "checker/check_all.py"], cwd=copy_, capture_output=True, text=True)
    assert r.returncode == 1, r.stdout  # no record, so no pass, but the tree is still the pool's
    assert "the tree is not the pool" not in r.stdout
    r = subprocess.run([sys.executable, "-I", "checker/attempts_check.py", POOL], cwd=copy_,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_the_gates_keep_the_two_apart(tmp_path):
    """Each workflow's gate takes only its own folder, so neither can carry the other's files."""
    if shutil.which("git") is None:
        pytest.skip("needs git (the check image has none; CI and a developer machine do)")
    repo = tmp_path / "pr"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
    (repo / "README.md").write_text("x")
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-qm", "base"], check=True)
    base = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    (repo / "attempts").mkdir()
    (repo / "attempts" / "a.json").write_text(json.dumps(GOOD))
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-qm", "attempt"], check=True)
    head = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    gate = str(ROOT / ".github" / "pr_gate.py")
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    ok = subprocess.run([sys.executable, "-I", gate, str(trusted), str(repo), "attempts", base, head],
                        capture_output=True, text=True)
    assert ok.returncode == 0 and (trusted / "attempts" / "a.json").exists(), ok.stdout
    refused = subprocess.run([sys.executable, "-I", gate, str(trusted), str(repo), "designs", base, head],
                             capture_output=True, text=True)
    assert refused.returncode == 1 and "refused" in refused.stdout
