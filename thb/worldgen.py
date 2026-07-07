"""Whole-world generation: all families in order with shared skill graph
and world memory, private manifests stored outside the public tree."""

import os
from typing import Any, Dict, List, Optional, Tuple

from .families import (f01_basic, f02_website, f03_api, f04_multirepo,
                       f05_youtube, f06_multilingual, f07_encoded,
                       f08_memory, f09_decoys, f10_grand)
from .families.registry import LevelResult, write_private_manifest
from .graphs.skills import SkillGraph
from .validate.leakage import scan_level
from .validate.one_answer import validate_one_answer
from .validate.oracle import OracleSolver

FAMILY_MODULES = {
    1: f01_basic, 2: f02_website, 3: f03_api, 4: f04_multirepo,
    5: f05_youtube, 6: f06_multilingual, 7: f07_encoded, 8: f08_memory,
    9: f09_decoys, 10: f10_grand,
}

# default plan: (family, sub_num) in dependency-safe order
DEFAULT_PLAN: List[Tuple[int, int]] = [
    (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1),
    (8, 1), (8, 2), (9, 1), (10, 1),
]


def generate_world(seed: int, split: str, out_root: str, world_id: str,
                   private_root: str,
                   plan: Optional[List[Tuple[int, int]]] = None,
                   validate: bool = True) -> List[Dict[str, Any]]:
    """Generate one world; returns a summary per level."""
    plan = plan or DEFAULT_PLAN
    skills = SkillGraph()
    memory: Dict[str, Any] = {}
    summaries = []
    results: List[LevelResult] = []
    for family, sub in plan:
        module = FAMILY_MODULES[family]
        result = module.generate(seed, split, out_root, world_id,
                                 sub_num=sub, skill_graph=skills,
                                 world_memory=memory)
        results.append(result)
    for result in results:
        reports = {}
        if validate:
            token, _events = OracleSolver(out_root).solve(
                result.private_manifest)
            assert token == result.token
            reports["leakage"] = scan_level(out_root,
                                            result.private_manifest)
            reports["one_answer"] = validate_one_answer(
                out_root, result.private_manifest)
            if not (reports["leakage"]["ok"] and reports["one_answer"]["ok"]):
                raise RuntimeError("level %s failed validation: %s"
                                   % (result.task_id, reports))
            result.private_manifest.validation_reports = {
                k: {"ok": v["ok"]} for k, v in reports.items()}
        write_private_manifest(result, private_root)
        summaries.append({
            "task_id": result.task_id,
            "run_id": result.run_id,
            "level_family": result.public_manifest.level_family,
            "start_repo": result.start_repo,
            "start_path": result.start_path,
            "repos": [r.name for r in result.repos],
            "validated": bool(reports),
        })
    return summaries
