"""Level Family 6: Multilingual and Cross-Lingual Clues.

Introduces ``cross_lingual_clue_following``: a German document instructs a
gold-price lookup whose rounded value names a branch; the branch holds an
Arabic document that routes to the terminal file. All values, paths, and
identifiers survive translation verbatim.
"""

from typing import Any, Dict, Optional

from ..gen.instructions import build_instruction_markdown
from ..graphs.skills import SkillGraph, skill_card_markdown
from ..sources.gold import GoldPriceSource, bundled_gold_dates
from .registry import LevelBuilder, LevelResult


def generate(seed: int, split: str, out_root: str, world_id: str,
             sub_num: int = 1, skill_graph: Optional[SkillGraph] = None,
             world_memory: Optional[Dict[str, Any]] = None) -> LevelResult:
    b = LevelBuilder(6, sub_num, seed, split, out_root, world_id,
                     skill_graph, world_memory)

    gold_date = b.rng.choice("gold_date", bundled_gold_dates())
    gold_int = b.resolve_source(GoldPriceSource(),
                                {"symbol": "GC=F", "date": gold_date},
                                "round_nearest_integer")
    gold_cache = b.last_cache_id()

    repo_name = b.forge.repo_name(label="main")
    branch = b.forge.branch_name(gold_int, label="gold")
    branch_pattern = branch.replace(gold_int, "{GOLD_INT}")
    de_code = b.rng.code("de_code", 4)
    ar_code = b.rng.code("ar_code", 4)
    start_path = "language_pack/%s_de_%s.md" % (b.level_tag, de_code)
    ar_path = "language_pack/%s_ar_%s.md" % (b.level_tag, ar_code)
    terminal_path = b.forge.file_path("terminal", ext="txt")

    if "get_gold_price" not in b.skills.skills:
        b.skills.introduce("get_gold_price", b.level_tag)
    else:
        b.skills.practice("get_gold_price", b.level_tag)
    b.skills.introduce("cross_lingual_clue_following", b.level_tag,
                       card_path=start_path)
    card = skill_card_markdown(
        "cross_lingual_clue_following",
        inputs="document in any supported language",
        normalization="values, dates, paths, and identifiers are copied "
                      "verbatim, never translated")

    de_doc = build_instruction_markdown(
        b.rng, "start", b.level_tag,
        [("translate_and_execute", {}),
         ("use_gold_source", {}),
         ("get_gold_for_date", {"date": gold_date}),
         ("round_nearest_var", {"var": "GOLD_INT"}),
         ("open_branch", {"branch": branch_pattern}),
         ("read_file", {"path": ar_path}),
         ("translate_and_execute", {})],
        lang="de",
        front_matter={"run_id": b.run_id},
        extra_sections=[{"heading": "Verfahrenskarte", "body": card}])
    ar_doc = build_instruction_markdown(
        b.rng, "arabic", b.level_tag,
        [("translate_and_execute", {}),
         ("final_file", {"path": terminal_path})],
        lang="ar",
        front_matter={"run_id": b.run_id})

    repo = b.new_repo(repo_name, "language records bundle")
    repo.add_commit("import language records", {
        start_path: de_doc,
        "notes/%s_scope.md" % b.level_tag:
            "# scope\nLanguage-pack ingest for this cycle.\n"})
    repo.add_commit("archive branch records",
                    {ar_path: ar_doc,
                     terminal_path: b.terminal_file_content()},
                    branch=branch)

    b.world.add("repo", {"repo": repo_name})
    b.world.add("file", {"repo": repo_name, "path": start_path})
    b.world.add("branch", {"repo": repo_name, "branch": branch},
                source_dependencies=[gold_cache])
    b.world.add("file", {"repo": repo_name, "path": ar_path,
                         "branch": branch})
    b.world.add("file", {"repo": repo_name, "path": terminal_path,
                         "branch": branch})

    b.chain.add("github_file", {"repo": repo_name, "path": start_path},
                "github", gold_date,
                skill_ids=["cross_lingual_clue_following",
                           "get_gold_price"])
    b.chain.add("api_value",
                {"source": GoldPriceSource.name,
                 "query": {"symbol": "GC=F", "date": gold_date},
                 "rule": "round_nearest_integer"},
                "external_api", gold_int,
                normalization="round_nearest_integer",
                source_cache_id=gold_cache, skill_ids=["get_gold_price"])
    b.chain.add("branch_doc",
                {"repo": repo_name, "branch": branch, "path": ar_path},
                "github", terminal_path,
                skill_ids=["cross_lingual_clue_following"])
    b.chain.add("terminal",
                {"repo": repo_name, "path": terminal_path, "branch": branch},
                "github", b.token)

    return b.finalize(repo_name, start_path,
                      allowed_tools=["github", "external_api", "file",
                                     "translation"],
                      approved_sources=["TreasureHuntBench GitHub",
                                        GoldPriceSource.name],
                      step_budget=100)
