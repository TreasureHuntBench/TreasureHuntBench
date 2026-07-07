"""Grep baseline.

Attempts to solve levels by regex sweeps alone: clue-boilerplate phrases and
token-shaped strings. On a well-formed world this must fail — boilerplate
never matches, and token-shaped strings are ambiguous because every level
also contains at least one fake token-shaped string.
"""

import os
import re
from typing import Any, Dict, List

TOKEN_RE = re.compile(r"THB\{[A-Za-z0-9]+\}")
BOILERPLATE_RES = [re.compile(p, re.IGNORECASE) for p in
                   [r"next[ _-]clue", r"final[ _-]answer", r"the clue is",
                    r"treasure is", r"secret", r"submit this"]]


def sweep(out_root: str) -> Dict[str, Any]:
    """Regex sweep over all public text artifacts of a world."""
    token_hits: Dict[str, List[str]] = {}
    boilerplate_hits: List[str] = []
    github_root = os.path.join(out_root, "github")
    for base, _dirs, files in os.walk(github_root):
        for name in files:
            full = os.path.join(base, name)
            rel = os.path.relpath(full, out_root).replace(os.sep, "/")
            try:
                with open(full, encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            for match in TOKEN_RE.findall(text):
                token_hits.setdefault(match, []).append(rel)
            for pattern in BOILERPLATE_RES:
                if pattern.search(text):
                    boilerplate_hits.append("%s:%s" % (pattern.pattern, rel))
    return {"token_candidates": sorted(token_hits),
            "token_locations": token_hits,
            "boilerplate_hits": boilerplate_hits}


def solve(out_root: str) -> Dict[str, Any]:
    """The baseline 'solves' a world only if the sweep is unambiguous."""
    report = sweep(out_root)
    candidates = report["token_candidates"]
    return {
        "solved": len(candidates) == 1,
        "candidate_count": len(candidates),
        "boilerplate_hit_count": len(report["boilerplate_hits"]),
        "report": report,
    }
