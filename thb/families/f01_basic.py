"""Level Family 1: Basic Clue Following.

A short deterministic trail across two repositories:
start runbook -> records file in the same repo -> document in a second
repository -> terminal file containing the final token.
"""

from typing import Any, Dict, Optional

from ..gen.instructions import build_instruction_markdown
from ..graphs.skills import SkillGraph
from .registry import LevelBuilder, LevelResult


def _filler_files(builder: LevelBuilder, label: str) -> Dict[str, str]:
    rng = builder.rng
    return {
        "notes/%s_%s_scope.md" % (builder.level_tag,
                                  rng.code("filler1:" + label, 3)):
            "# scope\nRoutine ingest notes for this bundle.\n",
        "tables/%s_%s_counts.csv" % (builder.level_tag,
                                     rng.code("filler2:" + label, 3)):
            "day,rows\n1,%d\n2,%d\n" % (rng.randint("f1:" + label, 40, 90),
                                        rng.randint("f2:" + label, 40, 90)),
    }


def generate(seed: int, split: str, out_root: str, world_id: str,
             sub_num: int = 1, skill_graph: Optional[SkillGraph] = None,
             world_memory: Optional[Dict[str, Any]] = None) -> LevelResult:
    b = LevelBuilder(1, sub_num, seed, split, out_root, world_id,
                     skill_graph, world_memory)

    start_repo = b.forge.repo_name(label="start")
    second_repo = b.forge.repo_name(label="second")
    start_path = b.forge.start_path()
    middle_path = b.forge.file_path("middle")
    terminal_path = b.forge.file_path("terminal", ext="txt")

    start_doc = build_instruction_markdown(
        b.rng, "start", b.level_tag,
        [("read_file", {"path": middle_path})],
        front_matter={"run_id": b.run_id})
    middle_doc = build_instruction_markdown(
        b.rng, "middle", b.level_tag,
        [("open_repo_named", {"repo": second_repo}),
         ("final_file", {"path": terminal_path})],
        front_matter={"run_id": b.run_id})

    repo1 = b.new_repo(start_repo, "ingest records bundle")
    repo1.add_commit("initial records import",
                     dict(_filler_files(b, "r1"), **{start_path: start_doc}))
    repo1.add_commit("add processing notes", {middle_path: middle_doc})

    repo2 = b.new_repo(second_repo, "archived review outputs")
    repo2.add_commit("archive review outputs",
                     dict(_filler_files(b, "r2"),
                          **{terminal_path: b.terminal_file_content()}))

    b.world.add("repo", {"repo": start_repo})
    b.world.add("file", {"repo": start_repo, "path": start_path})
    b.world.add("file", {"repo": start_repo, "path": middle_path})
    b.world.add("repo", {"repo": second_repo})
    b.world.add("file", {"repo": second_repo, "path": terminal_path})

    b.chain.add("github_file", {"repo": start_repo, "path": start_path},
                "github", middle_path)
    b.chain.add("github_file", {"repo": start_repo, "path": middle_path},
                "github", "%s %s" % (second_repo, terminal_path))
    b.chain.add("terminal", {"repo": second_repo, "path": terminal_path},
                "github", b.token)

    return b.finalize(start_repo, start_path,
                      allowed_tools=["github", "file"],
                      approved_sources=["TreasureHuntBench GitHub"],
                      step_budget=40)
