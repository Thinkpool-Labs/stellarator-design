"""What a design file may hold, checked before the scorer sees it.

A design is one JSON object:

    {"problem": "geometrical" | "simple_to_build" | "mhd_stable",
     "boundary": {"r_cos": [[...]], "z_sin": [[...]], "n_field_periods": 3,
                  "is_stellarator_symmetric": true},
     "notes": "optional, at most 2000 characters"}

`boundary` is ConStellaration's own SurfaceRZFourier in the JSON the leaderboard takes
(`SurfaceRZFourier.model_dump_json()`): r_cos and z_sin are (M + 1) x (2N + 1) arrays, row m for the
poloidal mode m = 0..M and column N + n for the toroidal mode n = -N..N. Only stellarator-symmetric
boundaries are taken (r_sin and z_cos absent or null), as on the leaderboard.

Every bound is checked on the raw JSON first, so nothing large or odd reaches numpy or pydantic.
"""
from __future__ import annotations

import math

PROBLEMS = ("geometrical", "simple_to_build", "mhd_stable")
MAX_POLOIDAL_ROWS = 16    # m = 0..15
MAX_TOROIDAL_COLS = 33    # n = -16..16
MAX_ABS_COEFF = 100.0
MAX_NOTES = 2000
TOP_KEYS = {"problem", "boundary", "notes"}
BOUNDARY_KEYS = {"r_cos", "z_sin", "n_field_periods", "is_stellarator_symmetric", "r_sin", "z_cos", "n_periodicity"}


def _matrix(name: str, v) -> tuple[int, int]:
    if not isinstance(v, list) or not v or len(v) > MAX_POLOIDAL_ROWS:
        raise ValueError(f"{name} must be a list of 1 to {MAX_POLOIDAL_ROWS} rows")
    cols = None
    for row in v:
        if not isinstance(row, list) or not row or len(row) > MAX_TOROIDAL_COLS:
            raise ValueError(f"{name}: each row is a list of 1 to {MAX_TOROIDAL_COLS} numbers")
        if cols is None:
            cols = len(row)
        elif len(row) != cols:
            raise ValueError(f"{name}: rows of different lengths")
        for x in row:
            if isinstance(x, bool) or not isinstance(x, (int, float)):
                raise ValueError(f"{name}: coefficients are numbers")
            if not math.isfinite(x) or abs(x) > MAX_ABS_COEFF:
                raise ValueError(f"{name}: coefficients are finite and at most {MAX_ABS_COEFF} in size")
    if cols % 2 != 1:
        raise ValueError(f"{name}: the number of columns is 2N + 1, an odd number")
    return len(v), cols


def validate(d) -> tuple[str, dict]:
    """Returns (problem, boundary dict) or raises ValueError."""
    if not isinstance(d, dict) or set(d) - TOP_KEYS or not {"problem", "boundary"} <= set(d):
        raise ValueError(f"a design has exactly the keys problem and boundary (and optionally notes)")
    if d["problem"] not in PROBLEMS:
        raise ValueError(f"problem is one of {', '.join(PROBLEMS)}")
    if "notes" in d and (not isinstance(d["notes"], str) or len(d["notes"]) > MAX_NOTES):
        raise ValueError(f"notes is a string of at most {MAX_NOTES} characters")
    b = d["boundary"]
    if not isinstance(b, dict) or set(b) - BOUNDARY_KEYS or not {"r_cos", "z_sin", "n_field_periods"} <= set(b):
        raise ValueError("boundary has r_cos, z_sin and n_field_periods (and is_stellarator_symmetric)")
    nfp = b["n_field_periods"]
    if isinstance(nfp, bool) or not isinstance(nfp, int) or not 1 <= nfp <= 10:
        raise ValueError("n_field_periods is an integer from 1 to 10")
    if b.get("is_stellarator_symmetric", True) is not True:
        raise ValueError("only stellarator-symmetric boundaries are taken")
    for k in ("r_sin", "z_cos"):
        if b.get(k) is not None:
            raise ValueError(f"{k} must be absent or null (stellarator symmetry)")
    if b.get("n_periodicity", 1) != 1:
        raise ValueError("n_periodicity, if given, is 1")
    if _matrix("r_cos", b["r_cos"]) != _matrix("z_sin", b["z_sin"]):
        raise ValueError("r_cos and z_sin have the same shape")
    if not b["r_cos"][0][len(b["r_cos"][0]) // 2] > 0:
        raise ValueError("r_cos at m = 0, n = 0 (the major radius) must be positive")
    clean = {"r_cos": b["r_cos"], "z_sin": b["z_sin"], "n_field_periods": nfp, "is_stellarator_symmetric": True}
    return d["problem"], clean
