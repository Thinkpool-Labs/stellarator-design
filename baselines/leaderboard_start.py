"""Day-one starting point: the leaderboard's current best boundary for a problem, as a design file.

    python baselines/leaderboard_start.py geometrical > start.json

Reads Proxima Fusion's public results dataset (proxima-fusion/constellaration-bench-results) through
the Hugging Face datasets server, so it needs the network: run it on your machine, never in a check.
The file it writes is the record itself, so submitting it unchanged earns nothing here; it is where a
polish (baselines/polish.py) or a new idea starts. For mhd_stable it writes the leaderboard's whole
best set as a JSON list of boundaries under "boundaries", one of which you would improve.

Each boundary on the leaderboard was submitted by someone (the "user" field); say whose design you
started from in your contribution's notes.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request

API = "https://datasets-server.huggingface.co/filter"
DATASET = "proxima-fusion/constellaration-bench-results"


def best(problem: str) -> dict:
    q = urllib.parse.urlencode({"dataset": DATASET, "config": "default", "split": "train",
                                "where": f"\"problem_type\"='{problem}'", "orderby": "\"score\" DESC",
                                "offset": 0, "length": 1})
    with urllib.request.urlopen(f"{API}?{q}", timeout=300) as r:
        rows = json.load(r)["rows"]
    if not rows:
        raise SystemExit(f"no rows for {problem}")
    return rows[0]["row"]


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("geometrical", "simple_to_build", "mhd_stable"):
        print(__doc__, file=sys.stderr)
        return 2
    p = sys.argv[1]
    row = best(p)
    note = f"started from {row['user']}'s leaderboard submission of {row['submission_time'][:10]} (score {row['score']:.6g})"
    if p == "mhd_stable":
        out = {"problem": p, "notes": note, "boundaries": [json.loads(b) for b in json.loads(row["boundary_json"])]}
    else:
        b = json.loads(row["boundary_json"])
        b.pop("n_periodicity", None)
        out = {"problem": p, "notes": note, "boundary": b}
    json.dump(out, sys.stdout)
    print(f"\n{note}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
