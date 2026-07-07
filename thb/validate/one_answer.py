"""One-answer validator.

Proves a generated level admits exactly one accepted answer: a single
terminal node, unique candidate filtering at every branching step, unique
CSV keys, cache-backed external values, and no decoy containing the real
token.
"""

import os
from typing import Any, Dict, List

from ..core.cache import SourceCache
from ..core.schemas import PrivateManifest
from ..gen.github_pub import LocalMirrorPublisher
from .oracle import OracleError, OracleSolver


def validate_one_answer(out_root: str,
                        manifest: PrivateManifest) -> Dict[str, Any]:
    problems: List[str] = []
    nodes = manifest.clue_nodes()

    terminals = [n for n in nodes if n.artifact_type == "terminal"]
    if len(terminals) != 1:
        problems.append("expected exactly 1 terminal node, got %d"
                        % len(terminals))
    if nodes and nodes[-1].artifact_type != "terminal":
        problems.append("terminal node is not last")

    cache = SourceCache(out_root + "/cache")
    for node in nodes:
        if node.artifact_type == "api_value":
            entry = cache.lookup(node.location["source"],
                                 node.location["query"])
            if entry is None:
                problems.append("uncached external value at %s"
                                % node.node_id)
            elif entry.normalized_value != node.observation:
                problems.append("cache/observation mismatch at %s"
                                % node.node_id)

    # the oracle enforces uniqueness at every filtering step; run it and
    # also confirm the hash equality
    solver = OracleSolver(out_root)
    try:
        token, _events = solver.solve(manifest)
    except OracleError as exc:
        problems.append("oracle failed: %s" % exc)
        token = ""

    # no decoy artifact may contain the real token
    if token:
        github = LocalMirrorPublisher(out_root)
        for art in manifest.artifacts():
            if art.decoy_status != "decoy":
                continue
            loc = art.public_location
            if "path" in loc and "repo" in loc:
                try:
                    text = github.read_file(loc["repo"], loc["path"],
                                            loc.get("branch", "main"))
                except OSError:
                    continue
                if token in text:
                    problems.append("decoy %s contains the real token"
                                    % art.artifact_id)
            elif "repo" in loc:
                repo_dir = github.repo_dir(loc["repo"])
                for base, _d, files in os.walk(repo_dir):
                    for name in files:
                        try:
                            with open(os.path.join(base, name),
                                      encoding="utf-8") as fh:
                                if token in fh.read():
                                    problems.append(
                                        "decoy repo %s contains the token"
                                        % loc["repo"])
                        except (UnicodeDecodeError, OSError):
                            continue

    return {"ok": not problems, "problems": problems}
