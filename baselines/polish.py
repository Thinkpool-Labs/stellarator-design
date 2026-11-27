"""A simple local polish around a design: perturb its Fourier coefficients, keep what helps.

    python baselines/polish.py start.json --minutes 60 --out polished.json [--seed 1]

This is a baseline to beat, not a method we expect to set records: (1+1) evolution with a step size
that adapts (grows on success, shrinks on failure), steps scaled by mode number like Proxima's own
ALM-NGOpt runner (higher modes move less), scored with ConStellaration's low-fidelity forward model
during the search and re-scored once at high fidelity, as the check does, at the end.

The search is penalised, not filtered: a candidate's merit is its score if feasible, else
score - 10 * (feasibility - tolerance), so it can walk through a slightly infeasible region. Only a
design the high-fidelity re-score calls feasible and better than RECORDS.json is worth a pull request.

Runs on your machine (one core per evaluation; --workers runs several at once).

What it did here (2026-11-27, 2 CPUs, 10 minutes, sigma 2e-3, from the geometrical record): 5
low-fidelity evaluations of the 10 x 21-mode design, one kept (low-fidelity score 0.980556 -> 0.980595),
and that one made high-fidelity VMEC++ fail to converge, so it scored nothing. Low fidelity accepting
what high fidelity can't solve is the first thing a better method has to handle; the default step is
now smaller.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent import futures
from pathlib import Path

import numpy as np

TOL = 1e-2


def _problem(name):
    from constellaration import problems
    return {"geometrical": problems.GeometricalProblem, "simple_to_build": problems.SimpleToBuildQIStellarator}[name]()


def merit(name: str, b: dict, fidelity: str) -> tuple[float, float, float]:
    """(merit, score, feasibility) of a boundary; -inf when the forward model fails."""
    from constellaration import forward_model
    from constellaration.geometry.surface_rz_fourier import SurfaceRZFourier
    from constellaration.mhd import vmec_settings

    p = _problem(name)
    s = SurfaceRZFourier.model_validate_json(json.dumps(b))
    if fidelity == "high":
        st = (forward_model.ConstellarationSettings.default_high_fidelity() if name != "geometrical"
              else forward_model.ConstellarationSettings.default_high_fidelity_skip_qi())
    else:
        low = vmec_settings.VmecPresetSettings(fidelity="low_fidelity")
        st = (forward_model.ConstellarationSettings(vmec_preset_settings=low, boozer_preset_settings=None, qi_settings=None)
              if name == "geometrical" else forward_model.ConstellarationSettings(vmec_preset_settings=low))
    try:
        m, _ = forward_model.forward_model(s, settings=st)
        feas = float(p.compute_feasibility(m))
        sc = float(p._score(m))
    except Exception as e:
        print(f"  ({fidelity} fidelity) the forward model failed: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr, flush=True)
        return float("-inf"), 0.0, float("inf")
    if not np.isfinite(sc) or not np.isfinite(feas):
        return float("-inf"), 0.0, float("inf")
    return (sc if feas <= TOL else sc - 10 * (feas - TOL)), sc, feas


def perturb(b: dict, sigma: float, rng) -> dict:
    r, z = np.array(b["r_cos"]), np.array(b["z_sin"])
    M, C = r.shape
    N = C // 2
    m = np.arange(M)[:, None]
    n = np.abs(np.arange(C) - N)[None, :]
    scale = sigma / (1.0 + m + n) ** 2
    mask = np.ones_like(r, dtype=bool)
    mask[0, : N + 1] = False          # m = 0, n <= 0: fixed by symmetry (and the major radius stays)
    r2 = r + rng.normal(size=r.shape) * scale * mask
    zmask = mask.copy()
    z2 = z + rng.normal(size=z.shape) * scale * zmask
    out = dict(b)
    out["r_cos"], out["z_sin"] = r2.tolist(), z2.tolist()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("start")
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--out", default="polished.json")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sigma", type=float, default=5e-4)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()
    d = json.loads(Path(a.start).read_text())
    name, best = d["problem"], d["boundary"]
    if name not in ("geometrical", "simple_to_build"):
        print("polish.py handles the single-objective problems", file=sys.stderr)
        return 2
    rng = np.random.default_rng(a.seed)
    bm, bs, bf = merit(name, best, "low")
    print(f"start: merit {bm:.6g} score {bs:.6g} feasibility {bf:.3g} (low fidelity)", flush=True)
    sigma, t_end, k = a.sigma, time.time() + 60 * a.minutes, 0
    with futures.ProcessPoolExecutor(a.workers) as ex:
        while time.time() < t_end:
            cands = [perturb(best, sigma, rng) for _ in range(a.workers)]
            for c, (m, s, f) in zip(cands, ex.map(merit, [name] * len(cands), cands, ["low"] * len(cands))):
                k += 1
                if m > bm:
                    best, bm, bs, bf = c, m, s, f
                    sigma *= 1.5
                    print(f"[{k}] merit {bm:.6g} score {bs:.6g} feasibility {bf:.3g} sigma {sigma:.2g}", flush=True)
                else:
                    sigma *= 0.9 ** (1 / 4)
            sigma = float(np.clip(sigma, 1e-6, 5e-2))
    hm, hs, hf = merit(name, best, "high")
    print(f"high fidelity: score {hs:.6g} feasibility {hf:.3g} ({'feasible' if hf <= TOL else 'NOT feasible'})", flush=True)
    note = (d.get("notes", "") + f"; polished with baselines/polish.py seed {a.seed}, {k} evaluations").strip("; ")[:2000]
    Path(a.out).write_text(json.dumps({"problem": name, "boundary": best, "notes": note}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
