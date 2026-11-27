"""The pool's check: every new design is scored, and at least one beats the record for its problem.

    python checker/check_all.py

Designs already scored (listed with their sha256 in RECORDS.json under "scored") are skipped, so a
check scores only what a contribution adds. Each new design is scored by Proxima Fusion's own
ConStellaration scorer in a child process with a time limit; a design the scorer can't evaluate, or
that runs past the limit, is INVALID and fails the check.

Exit 0 when every new design is valid and feasible and at least one is a record:
  geometrical, simple_to_build: a score higher than the record's by more than MIN_SCORE_GAIN
  mhd_stable: adds more than front.MIN_GAIN to the hypervolume of the record front
Exit 1 otherwise. Thinkpool runs this without and with a contribution's diff: a new record fails
before and passes after.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "checker"))

from front import MIN_GAIN, gain, to_min  # noqa: E402
from hygiene import problems  # noqa: E402

MAX_NEW = 1            # one new design per contribution
TIME_LIMIT_S = 2400    # per design: VMEC++ at high fidelity took 555 s on a 10x21 boundary on one core
MIN_SCORE_GAIN = 1e-6
MAX_FILES = 500


def score_child(raw: bytes) -> dict:
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "LANG", "TMPDIR"}}
    env.update(OMP_NUM_THREADS="2", MPLCONFIGDIR="/tmp")
    try:
        r = subprocess.run([sys.executable, "-I", str(ROOT / "checker" / "evaluate_one.py")], input=raw,
                           capture_output=True, timeout=TIME_LIMIT_S, env=env)
    except subprocess.TimeoutExpired:
        return {"verdict": "INVALID", "reason": f"the scorer ran past {TIME_LIMIT_S} s"}
    lines = [ln for ln in r.stdout.decode("utf-8", "replace").splitlines() if ln.startswith("{")]
    if not lines:
        return {"verdict": "INVALID", "reason": f"the scorer stopped (exit {r.returncode}) without an answer"}
    return json.loads(lines[-1])


def main() -> int:
    bad = problems(ROOT, "designs")
    if bad:
        print(json.dumps({"summary": "the tree is not the pool's", "problems": bad[:20]}))
        return 1
    rec = json.loads((ROOT / "RECORDS.json").read_text(encoding="utf-8"))
    scored = {s["sha256"] for s in rec["scored"]}
    best = {p: rec["records"][p]["score"] for p in ("geometrical", "simple_to_build")}
    front = [to_min(p) for p in rec["records"]["mhd_stable"]["front"]]
    files = sorted((ROOT / "designs").glob("*.json"))
    if len(files) > MAX_FILES:
        print(json.dumps({"summary": "too many design files", "limit": MAX_FILES}))
        return 1
    fresh = []
    for f in files:
        if f.is_symlink() or not f.is_file():
            print(json.dumps({"file": f.name, "verdict": "MALFORMED", "reason": "not a regular file"}))
            return 1
        raw = f.read_bytes()
        if hashlib.sha256(raw).hexdigest() not in scored:
            fresh.append((f, raw))
    if len(fresh) > MAX_NEW:
        print(json.dumps({"summary": f"one new design per contribution (found {len(fresh)})", "new_files": [f.name for f, _ in fresh]}))
        return 1
    ok, new = True, []
    for f, raw in fresh:
        out = score_child(raw)
        out["file"] = f.name
        print(json.dumps(out))
        if out.get("verdict") != "VALID" or not out.get("feasible"):
            ok = False
            continue
        p = out["problem"]
        if p == "mhd_stable":
            g = gain(front, to_min(out["point"]))
            out["hypervolume_gain"] = g
            if g > MIN_GAIN:
                new.append({"file": f.name, "problem": p, "hypervolume_gain": g})
        elif out["score"] > best[p] + MIN_SCORE_GAIN:
            new.append({"file": f.name, "problem": p, "score": out["score"], "record": best[p]})
    summary = "ok" if ok and new else ("a design is not valid or not feasible" if not ok else
                                       "no new design" if not fresh else "no new record")
    print(json.dumps({"summary": summary, "new": new}))
    return 0 if ok and new else 1


if __name__ == "__main__":
    sys.exit(main())
