"""Tests of the checker. Run inside the pool's image:

    docker run --rm --network none -v "$PWD:/work" -w /work thinkpool-prometheus-cst:1 python -m pytest tests -q

The tests marked slow run the real scorer (a minute or more each) and are skipped with -m "not slow".
"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "checker"))

import check_all  # noqa: E402
import evaluate_one  # noqa: E402
from design import validate  # noqa: E402
from front import gain, hypervolume, to_min  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"


def boundary(rows=3, cols=5, nfp=3):
    r = [[0.0] * cols for _ in range(rows)]
    z = [[0.0] * cols for _ in range(rows)]
    r[0][cols // 2] = 1.0
    r[1][cols // 2] = 0.1
    z[1][cols // 2] = 0.1
    return {"r_cos": r, "z_sin": z, "n_field_periods": nfp, "is_stellarator_symmetric": True}


def test_accepts_a_plain_boundary():
    assert validate({"problem": "geometrical", "boundary": boundary()})[0] == "geometrical"


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(problem="fusion"),
    lambda d: d.update(extra=1),
    lambda d: d["boundary"].update(r_cos=[[float("nan")] * 5] * 3),
    lambda d: d["boundary"].update(r_cos=[[1e300] * 5] * 3),
    lambda d: d["boundary"].update(r_cos=[[True] * 5] * 3),
    lambda d: d["boundary"].update(r_cos=[["1"] * 5] * 3),
    lambda d: d["boundary"].update(z_sin=[[0.0] * 5] * 2),
    lambda d: d["boundary"].update(r_cos=[[0.0] * 4] * 3, z_sin=[[0.0] * 4] * 3),
    lambda d: d["boundary"].update(r_cos=[[0.0] * 5] * 3),          # major radius 0
    lambda d: d["boundary"].update(is_stellarator_symmetric=False),
    lambda d: d["boundary"].update(r_sin=[[0.0] * 5] * 3),
    lambda d: d["boundary"].update(n_field_periods=0),
    lambda d: d["boundary"].update(n_field_periods=3.0),
    lambda d: d.update(notes="x" * 3000),
])
def test_refuses_odd_input(mutate):
    d = {"problem": "geometrical", "boundary": boundary()}
    mutate(d)
    with pytest.raises(ValueError):
        validate(d)


def test_refuses_huge_arrays_fast():
    t = time.time()
    big = {"problem": "geometrical", "boundary": boundary(rows=17, cols=5)}
    with pytest.raises(ValueError):
        validate(big)
    wide = {"problem": "geometrical", "boundary": boundary(rows=3, cols=35)}
    with pytest.raises(ValueError):
        validate(wide)
    assert time.time() - t < 0.5


def test_json_nan_never_reaches_the_scorer(monkeypatch, capsys):
    # json.loads accepts NaN; the shape check must refuse it before scoring.
    called = []
    monkeypatch.setattr(evaluate_one, "score", lambda *a: called.append(1))
    b = boundary()
    text = json.dumps({"problem": "geometrical", "boundary": b}).replace("0.1", "NaN", 1)
    monkeypatch.setattr(sys, "stdin", io.StringIO(text))
    evaluate_one.main()
    assert json.loads(capsys.readouterr().out)["verdict"] == "MALFORMED" and not called


def test_scorer_exception_is_invalid(monkeypatch, capsys):
    def boom(*a):
        raise ValueError("Minimum of B is at the boundary.")
    monkeypatch.setattr(evaluate_one, "score", boom)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"problem": "simple_to_build", "boundary": boundary()})))
    evaluate_one.main()
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "INVALID" and "Minimum of B" in out["reason"]


def test_a_design_past_its_time_is_invalid(monkeypatch):
    monkeypatch.setattr(check_all, "TIME_LIMIT_S", 1)
    out = check_all.score_child(json.dumps({"problem": "geometrical", "boundary": boundary()}).encode())
    assert out["verdict"] == "INVALID" and "ran past" in out["reason"]


def test_hypervolume_matches_pymoo():
    from pymoo.indicators import hv
    rng = np.random.default_rng(1)
    for _ in range(20):
        pts = [to_min((rng.uniform(0, 20), rng.uniform(2, 22))) for _ in range(rng.integers(1, 40))]
        ours = hypervolume(pts)
        X = np.array([p for p in pts if p[0] < 1 and p[1] < 20]) if pts else None
        theirs = hv.Hypervolume(ref_point=np.array([1.0, 20.0]))(X) if X is not None and len(X) else 0.0
        assert abs(ours - theirs) < 1e-9 * max(1.0, theirs)


def test_record_front_matches_the_leaderboard():
    rec = json.loads((ROOT / "RECORDS.json").read_text())["records"]["mhd_stable"]
    hv_ = hypervolume([to_min(p) for p in rec["front"]])
    assert abs(hv_ - rec["leaderboard_best_set_hypervolume"]) < 1e-6
    # a point of the front adds nothing; a point beyond it adds something
    front = [to_min(p) for p in rec["front"]]
    assert gain(front, front[0]) == 0
    lgb, ar = rec["front"][0]
    assert gain(front, to_min((lgb + 1, ar))) > 0


def test_without_new_designs_the_check_fails():
    r = subprocess.run([sys.executable, "-I", "checker/check_all.py"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 1, r.stdout


def _pool_copy(tmp_path):
    copy = tmp_path / "pool"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    return copy


@pytest.mark.slow
def test_leaderboard_design_scores_as_the_leaderboard_said():
    d = json.loads((FIX / "leaderboard-geometrical-top.json").read_text())
    out = check_all.score_child(json.dumps({"problem": d["problem"], "boundary": d["boundary"]}).encode())
    assert out["verdict"] == "VALID" and out["feasible"], out
    assert abs(out["score"] - d["leaderboard"]["score"]) < 1e-6, out


@pytest.mark.slow
def test_a_better_design_passes_and_a_worse_one_fails(tmp_path):
    copy = _pool_copy(tmp_path)
    d = json.loads((FIX / "leaderboard-geometrical-top.json").read_text())
    (copy / "designs" / "try.json").write_text(json.dumps({"problem": "geometrical", "boundary": d["boundary"]}))
    run = lambda: subprocess.run([sys.executable, "-I", "checker/check_all.py"], cwd=copy, capture_output=True, text=True)
    r = run()  # the leaderboard's own best is not a record here
    assert r.returncode == 1 and "no new record" in r.stdout, r.stdout
    rec = json.loads((copy / "RECORDS.json").read_text())
    rec["records"]["geometrical"]["score"] = 0.9
    (copy / "RECORDS.json").write_text(json.dumps(rec))
    r = run()
    assert r.returncode == 0 and '"summary": "ok"' in r.stdout, r.stdout
