"""The MHD-stable problem's front, and what one more design adds to it.

The leaderboard scores a *set* of boundaries for this problem: the hypervolume, over the feasible
ones, of the points (-L_gradB, aspect ratio) against the reference point (1, 20), both minimised
(constellaration.problems.MHDStableQIStellarator._score, which calls pymoo). Scoring a whole set of
hundreds of boundaries does not fit one check, so here a contribution is one boundary, and it is a
record when it is feasible and adds more than MIN_GAIN to the hypervolume of the record front in
RECORDS.json. Adding a point never lowers a hypervolume, so a set of such contributions merged
together beats the leaderboard's best set by at least the sum of what they added.

Two dimensions make the hypervolume exact and short to compute, so the pool does not depend on
pymoo for it; tests/ compare this with pymoo.
"""
from __future__ import annotations

REF = (1.0, 20.0)
MIN_GAIN = 1e-3


def to_min(point) -> tuple[float, float]:
    """(L_gradB, aspect ratio) as reported -> the minimised pair (-L_gradB, aspect ratio)."""
    lgb, ar = point
    return (-float(lgb), float(ar))


def hypervolume(points) -> float:
    pts = sorted(p for p in (tuple(map(float, q)) for q in points) if p[0] < REF[0] and p[1] < REF[1])
    # sorted by x ascending: keep the falling staircase of y, then sum its strips
    hv, stair = 0.0, []
    for x, y in pts:
        if not stair or y < stair[-1][1]:
            stair.append((x, y))
    for i, (x, y) in enumerate(stair):
        x_next = stair[i + 1][0] if i + 1 < len(stair) else REF[0]
        hv += (x_next - x) * (REF[1] - y)
    return hv


def gain(front, point) -> float:
    return hypervolume(list(front) + [point]) - hypervolume(front)
