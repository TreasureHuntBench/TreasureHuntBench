"""Leakage scanner.

Rejects a generated level if any public artifact would let an agent shortcut
the intended path: clue boilerplate, predictable filenames, the final token
outside the intended terminal artifact, or private-manifest exposure.
"""

import os
import re
from typing import Any, Dict, List

from ..core.naming import (BANNED_PHRASES, contains_banned_phrase,
                           is_banned_basename)
from ..core.schemas import PrivateManifest

_PRIVATE_MARKERS = ["final_token_hash", "oracle_trace", "clue_graph"]

_GREP_SHORTCUTS = [r"next[ _-]clue", r"final[ _-]answer", r"the clue is",
                   r"treasure(?!huntbench)", r"secret", r"submit this"]


def _public_files(out_root: str):
    for base, _dirs, files in os.walk(out_root):
        rel_base = os.path.relpath(base, out_root).replace(os.sep, "/")
        if rel_base.startswith(("tasks",)):
            continue  # manifests are benchmark metadata, not world artifacts
        for name in files:
            yield os.path.join(base, name), "%s/%s" % (rel_base, name)


def scan_level(out_root: str, manifest: PrivateManifest) -> Dict[str, Any]:
    violations: List[str] = []
    terminal = manifest.clue_nodes()[-1]
    terminal_suffix = "branches/%s/%s" % (
        terminal.location.get("branch", "main"), terminal.location["path"])
    terminal_repo = terminal.location["repo"]

    # recover the token indirectly: read the terminal artifact
    terminal_file = os.path.join(out_root, "github", terminal_repo,
                                 terminal_suffix)
    token = ""
    if os.path.exists(terminal_file):
        with open(terminal_file, encoding="utf-8") as fh:
            token = fh.read().strip()
    else:
        violations.append("terminal artifact missing: %s" % terminal_suffix)

    for full, rel in _public_files(out_root):
        if is_banned_basename(rel):
            violations.append("banned basename: %s" % rel)
        try:
            with open(full, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        hit = contains_banned_phrase(text)
        if hit:
            violations.append("banned phrase %r in %s" % (hit, rel))
        scrubbed = re.sub(r"treasurehuntbench", "", text,
                          flags=re.IGNORECASE)
        for pattern in _GREP_SHORTCUTS:
            if re.search(pattern, scrubbed, re.IGNORECASE):
                violations.append("grep shortcut %r matches %s"
                                  % (pattern, rel))
        if token and token in text:
            in_terminal = rel.endswith(terminal_suffix)
            in_own_history = (rel == "github/%s/history.json" % terminal_repo)
            if not (in_terminal or in_own_history):
                violations.append("final token exposed in %s" % rel)
        for marker in _PRIVATE_MARKERS:
            if '"%s"' % marker in text and rel.startswith("github/"):
                violations.append("private manifest field %r in %s"
                                  % (marker, rel))

    return {"ok": not violations, "violations": violations,
            "checked_banned_phrases": len(BANNED_PHRASES)}
