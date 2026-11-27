"""Fetch the leaderboard designs the slow tests score, into tests/fixtures/ (not committed).

    python tests/fetch_fixtures.py

The leaderboard's results dataset carries no licence, so this repository does not redistribute its
boundaries; the slow tests skip until this has been run. Needs the network; the tests do not.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "baselines"))

from leaderboard_start import DATASET, best  # noqa: E402

SOURCE = f"https://huggingface.co/datasets/{DATASET}"


def main() -> int:
    out = ROOT / "tests" / "fixtures"
    out.mkdir(exist_ok=True)
    row = best("geometrical")
    b = json.loads(row["boundary_json"])
    b.pop("n_periodicity", None)
    (out / "leaderboard-geometrical-top.json").write_text(json.dumps({
        "problem": "geometrical", "boundary": b,
        "leaderboard": {"user": row["user"], "submitted": row["submission_time"], "score": row["score"], "source": SOURCE},
    }))
    row = best("mhd_stable")
    b = json.loads(json.loads(row["boundary_json"])[0])
    b.pop("n_periodicity", None)
    (out / "leaderboard-mhd-front-point.json").write_text(json.dumps({
        "problem": "mhd_stable", "boundary": b,
        "leaderboard": {"user": row["user"], "submitted": row["submission_time"], "set_member": 0, "source": SOURCE},
    }))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
