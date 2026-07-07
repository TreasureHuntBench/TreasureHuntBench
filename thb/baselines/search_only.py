"""Search-only baseline.

Knows the public manifest (start artifact, its run_id) and tries to jump to
an answer by searching artifacts that mention the run id, without following
the clue path. Must fail: the run id appears in routing documents, and the
only token-shaped string co-located with it is the planted fake.
"""

import os
import re
from typing import Any, Dict, List

from .grep_baseline import TOKEN_RE


def solve(out_root: str, run_id: str) -> Dict[str, Any]:
    github_root = os.path.join(out_root, "github")
    tagged_repos: List[str] = []
    for repo in sorted(os.listdir(github_root) if os.path.isdir(github_root)
                       else []):
        rdir = os.path.join(github_root, repo)
        for base, _dirs, files in os.walk(rdir):
            for name in files:
                try:
                    with open(os.path.join(base, name),
                              encoding="utf-8") as fh:
                        if re.search(r"run_id:?\s*%s" % re.escape(run_id),
                                     fh.read()):
                            tagged_repos.append(repo)
                            raise StopIteration
                except StopIteration:
                    break
                except (UnicodeDecodeError, OSError):
                    continue
            else:
                continue
            break
    # collect token-shaped strings only from run_id-tagged repos
    candidates = set()
    for repo in tagged_repos:
        rdir = os.path.join(github_root, repo)
        for base, _dirs, files in os.walk(rdir):
            for name in files:
                try:
                    with open(os.path.join(base, name),
                              encoding="utf-8") as fh:
                        candidates.update(TOKEN_RE.findall(fh.read()))
                except (UnicodeDecodeError, OSError):
                    continue
    return {"solved": len(candidates) == 1,
            "candidates": sorted(candidates),
            "tagged_repos": tagged_repos}
