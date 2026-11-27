"""Check the attempts log: every file in attempts/ is a well-formed record of work that set no record.

    python -I checker/attempts_check.py <pool name>

An attempt is how a pool keeps days of effort that fell short: what was tried, how far it got, what it
cost, where to reproduce it and why it stopped. It earns no record and no points; it saves the next
person from repeating it. The schema is strict and every field is bounded, so a file is data and never
markup: free text may not carry control or bidirectional-override characters, and links go to GitHub,
arXiv or DOI only. Exit 0 when every file is valid, 1 otherwise. Standard library only.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "attempts"
MAX_FILES = 2000
MAX_BYTES = 64_000
SCHEMA = "thinkpool-attempt/1"
OUTCOMES = {"no_improvement", "matched_record", "partial", "inconclusive", "checker_issue"}
KEYS = {"schema", "pool", "author", "date", "target", "approach", "best_value", "outcome", "why",
        "compute", "artifact", "references", "tags"}
REQUIRED = KEYS - {"best_value", "references", "tags"}
HANDLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TAG = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REL_PATH = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]{0,200}$")
GITHUB_URL = re.compile(
    r"^https://(?:github\.com|gist\.github\.com)/[A-Za-z0-9][A-Za-z0-9._/-]{0,300}(?:#[A-Za-z0-9_-]{0,80})?$")
REF_URL = re.compile(r"^https://(?:arxiv\.org|doi\.org|github\.com|gist\.github\.com)/[A-Za-z0-9._/:%()-]{1,300}$")
# C0 and C1 controls (tab and newline are allowed in long text), DEL, the line and paragraph
# separators, the byte-order mark and every bidirectional mark or override. Built from code points.
_BAD = (list(range(0, 9)) + [11, 12] + list(range(13, 32)) + [127] + list(range(0x80, 0xA0))
        + [0x200E, 0x200F, 0x2028, 0x2029, 0xFEFF] + list(range(0x202A, 0x202F)) + list(range(0x2066, 0x206A)))
BAD_CHARS = re.compile("[" + "".join(re.escape(chr(c)) for c in _BAD) + "]")


def text(v, name: str, limit: int, multiline: bool = False) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{name}: a non-empty string")
    if len(v) > limit:
        raise ValueError(f"{name}: at most {limit} characters")
    if BAD_CHARS.search(v) or (not multiline and ("\n" in v or "\t" in v)):
        raise ValueError(f"{name}: control or direction-override characters are not accepted")
    return v


def link(v, name: str) -> None:
    if not isinstance(v, str) or not GITHUB_URL.match(v):
        raise ValueError(f"{name}: a github.com or gist.github.com link (a commit, a file at a commit, a gist)")


def judge(a, pool: str) -> dict:
    if not isinstance(a, dict):
        raise ValueError("an attempt is a JSON object")
    extra, missing = set(a) - KEYS, REQUIRED - set(a)
    if extra or missing:
        raise ValueError(f"keys: unknown {sorted(extra)}, missing {sorted(missing)}")
    if a["schema"] != SCHEMA:
        raise ValueError(f"schema: must be {SCHEMA!r}")
    if a["pool"] != pool:
        raise ValueError(f"pool: this is {pool!r}")
    if not isinstance(a["author"], str) or not HANDLE.match(a["author"]):
        raise ValueError("author: a GitHub handle")
    if not isinstance(a["date"], str) or not DAY.match(a["date"]):
        raise ValueError("date: YYYY-MM-DD")
    d = date.fromisoformat(a["date"])
    if not date(2020, 1, 1) <= d <= date.today():
        raise ValueError("date: not a plausible date")
    text(a["target"], "target", 200)
    text(a["approach"], "approach", 4000, multiline=True)
    text(a["why"], "why", 4000, multiline=True)
    if a.get("best_value") is not None:
        text(a["best_value"], "best_value", 100)
    if a["outcome"] not in OUTCOMES:
        raise ValueError(f"outcome: one of {sorted(OUTCOMES)}")

    c = a["compute"]
    if not isinstance(c, dict) or set(c) - {"hours", "hardware"} or "hours" not in c:
        raise ValueError("compute: {hours, hardware?}")
    h = c["hours"]
    if isinstance(h, bool) or not isinstance(h, (int, float)) or not 0 <= h <= 100_000:
        raise ValueError("compute.hours: a number from 0 to 100000")
    if "hardware" in c:
        text(c["hardware"], "compute.hardware", 200)

    art = a["artifact"]
    if not isinstance(art, dict) or set(art) not in ({"url"}, {"url", "path", "sha256"}):
        raise ValueError("artifact: {url} or {url, path, sha256}")
    link(art["url"], "artifact.url")
    if "path" in art:
        if not isinstance(art["path"], str) or not REL_PATH.match(art["path"]) or ".." in art["path"].split("/"):
            raise ValueError("artifact.path: a relative path inside the linked repository")
        if not isinstance(art["sha256"], str) or not SHA256.match(art["sha256"]):
            raise ValueError("artifact.sha256: 64 lower-case hex digits")

    refs = a.get("references", [])
    if not isinstance(refs, list) or len(refs) > 10 or not all(isinstance(r, str) and REF_URL.match(r) for r in refs):
        raise ValueError("references: up to 10 arxiv.org, doi.org or GitHub links")
    tags = a.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 10 or not all(isinstance(t, str) and TAG.match(t) for t in tags):
        raise ValueError("tags: up to 10 lower-case slugs")
    return {"verdict": "VALID", "target": a["target"], "outcome": a["outcome"]}


def main(pool: str) -> int:
    if not DIR.is_dir():
        print(json.dumps({"summary": "no attempts/ folder"}))
        return 1
    files = sorted(p for p in DIR.iterdir() if p.name != "README.md")
    if len(files) > MAX_FILES:
        print(json.dumps({"summary": "too many attempt files", "limit": MAX_FILES}))
        return 1
    ok = True
    for f in files:
        try:
            if f.is_symlink() or not f.is_file() or f.suffix != ".json":
                raise ValueError("only regular JSON files directly in attempts/")
            if f.stat().st_size > MAX_BYTES:
                raise ValueError(f"larger than {MAX_BYTES} bytes")
            out = judge(json.loads(f.read_bytes().decode("utf-8")), pool)
        except Exception as e:  # noqa: BLE001
            out = {"verdict": "MALFORMED", "reason": str(e)}
            ok = False
        out["file"] = f.name
        print(json.dumps(out))
    print(json.dumps({"summary": "ok" if ok else "an attempt is not valid", "files": len(files)}))
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: attempts_check.py <pool name>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
