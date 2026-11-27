# The attempts log

Most days spent on stellarator design end without a record. That work is still worth something: the next person
should know that a CMA-ES run from the rotating-ellipse start on simple_to_build was tried, how far it got and why it stopped. `attempts/` keeps it.

An attempt earns no record and no points. It is how this pool remembers what didn't work, so effort
adds up instead of repeating. A maintainer reads each one before merging it, and may ask for detail.

## Add one

A pull request that adds one JSON file to `attempts/` and nothing else, named
`YYYY-MM-DD-<your-handle>-<short-slug>.json`:

```json
{
  "schema": "thinkpool-attempt/1",
  "pool": "stellarator-design",
  "author": "your-github-handle",
  "date": "2026-11-27",
  "target": "simple_to_build above 0.6956",
  "approach": "What you tried, in enough detail that someone could repeat it.",
  "best_value": "0.62 (feasible, below the record)",
  "outcome": "no_improvement",
  "why": "Where it stalled, and your best guess why. Dead ends are the useful part.",
  "compute": {"hours": 6.5, "hardware": "laptop, 8 cores"},
  "artifact": {"url": "https://github.com/you/repo/blob/<commit>/search.py", "path": "search.py", "sha256": "<64 hex>"},
  "references": ["https://arxiv.org/abs/..."],
  "tags": ["local-search"]
}
```

- `outcome` is one of `no_improvement`, `matched_record`, `partial` (a sub-result: a smaller case, a
  better start, a speed-up), `inconclusive` (ran out of time), `checker_issue` (you think the checker or
  the records are wrong: say how).
- `artifact` points at code you can share, on GitHub: a commit, a file at a commit, or a gist. With
  `path` and `sha256`, readers can tell they have the file you ran. `best_value`, `references` and
  `tags` are optional.
- Text fields are plain text: no control characters. Links go to GitHub, arXiv or doi.org only.

Check it before you send it: `python checker/attempts_check.py stellarator-design`.

The `attempts` workflow checks the file with the base branch's own checker, as the record check does,
and executes nothing from your pull request. Send a record and an attempt as two pull requests: each
workflow refuses the other's files.
