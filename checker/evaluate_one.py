"""Score one design with Proxima Fusion's own scorer. Run as a child of check_all.py:

    python -I checker/evaluate_one.py < design.json

Prints one JSON line. A boundary the scorer cannot evaluate (VMEC++ does not converge, the QI
calculation raises, anything else) is reported as INVALID with the scorer's own reason: a design
that can't be scored scores nothing. check_all.py kills this process when it runs past its time.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from design import validate  # noqa: E402


def score(problem: str, boundary: dict) -> dict:
    import numpy as np
    from constellaration import forward_model, problems
    from constellaration.geometry.surface_rz_fourier import SurfaceRZFourier

    surface = SurfaceRZFourier.model_validate_json(json.dumps(boundary))
    if problem == "geometrical":
        ev = problems.GeometricalProblem().evaluate(surface)
        return {"verdict": "VALID", "problem": problem, "feasible": ev.score > 0, "score": float(ev.score),
                "objective": float(ev.objective), "feasibility": float(ev.feasibility)}
    if problem == "simple_to_build":
        ev = problems.SimpleToBuildQIStellarator().evaluate(surface)
        return {"verdict": "VALID", "problem": problem, "feasible": ev.score > 0, "score": float(ev.score),
                "objective": float(ev.objective), "feasibility": float(ev.feasibility)}
    # mhd_stable: one boundary, scored as a point of the (L_gradB, aspect ratio) front.
    p = problems.MHDStableQIStellarator()
    m, _ = forward_model.forward_model(boundary=surface, settings=forward_model.ConstellarationSettings.default_high_fidelity())
    feasible = p.is_feasible(m)
    lgb = float(m.minimum_normalized_magnetic_gradient_scale_length)
    ar = float(m.aspect_ratio)
    if not (np.isfinite(lgb) and np.isfinite(ar)):
        raise ValueError("the scorer returned a non-finite objective")
    return {"verdict": "VALID", "problem": problem, "feasible": bool(feasible), "point": [lgb, ar],
            "feasibility": float(p.compute_feasibility(m))}


def main() -> int:
    try:
        problem, boundary = validate(json.loads(sys.stdin.read()))
    except Exception as e:
        print(json.dumps({"verdict": "MALFORMED", "reason": str(e)[:500]}))
        return 0
    try:
        out = score(problem, boundary)
    except Exception as e:
        out = {"verdict": "INVALID", "problem": problem,
               "reason": f"the scorer could not evaluate this boundary: {type(e).__name__}: {str(e)[:400]}",
               "where": traceback.format_exc(limit=2)[-400:]}
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
