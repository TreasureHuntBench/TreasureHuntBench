"""Level Family 4: Multi-Repository Search and Filtering.

Reuses ``get_gold_price`` and introduces
``search_and_filter_repositories``: the rounded gold close keys a repository
name pattern that several near-duplicate repositories match; only the one
whose keyed records file carries the task's run id is valid.
"""

from typing import Any, Dict, Optional

from ..gen.decoys import perturb_ref
from ..gen.instructions import build_instruction_markdown
from ..graphs.skills import SkillGraph, skill_card_markdown
from ..sources.gold import GoldPriceSource, bundled_gold_dates
from .registry import LevelBuilder, LevelResult

N_CANDIDATES = 4  # one real + three rule-invalid


def generate(seed: int, split: str, out_root: str, world_id: str,
             sub_num: int = 1, skill_graph: Optional[SkillGraph] = None,
             world_memory: Optional[Dict[str, Any]] = None) -> LevelResult:
    b = LevelBuilder(4, sub_num, seed, split, out_root, world_id,
                     skill_graph, world_memory)

    gold_date = b.rng.choice("gold_date", bundled_gold_dates())
    gold_int = b.resolve_source(GoldPriceSource(),
                                {"symbol": "GC=F", "date": gold_date},
                                "round_nearest_integer")
    gold_cache = b.last_cache_id()

    stem = b.forge.repo_stem()
    pattern = "%s_%s_*" % (stem, gold_int)
    codes = []
    for i in range(N_CANDIDATES):
        code = b.rng.code("cand_code:%d" % i, 2)
        while code in codes:
            code += "X"
        codes.append(code)
    real_code = b.rng.choice("real_code", codes)
    real_repo = "%s_%s_%s" % (stem, gold_int, real_code)

    start_repo = b.forge.repo_name(label="start")
    start_path = b.forge.start_path()
    final_repo = b.forge.repo_name(label="final")
    terminal_path = b.forge.file_path("terminal", ext="txt")

    if "get_gold_price" not in b.skills.skills:
        b.skills.introduce("get_gold_price", b.level_tag)
    else:
        b.skills.practice("get_gold_price", b.level_tag)
    b.skills.introduce("search_and_filter_repositories", b.level_tag,
                       card_path=start_path)
    card = skill_card_markdown(
        "search_and_filter_repositories",
        inputs="organization, name pattern, per-candidate metadata file, "
               "task-specific selection field",
        normalization="exactly one candidate satisfies the stated condition")

    start_doc = build_instruction_markdown(
        b.rng, "start", b.level_tag,
        [("use_gold_source", {}),
         ("get_gold_for_date", {"date": gold_date}),
         ("round_nearest_var", {"var": "GOLD_INT"}),
         ("search_repos_pattern", {"pattern": "%s_{GOLD_INT}_*" % stem}),
         ("read_candidates", {"path_template": "records/<repository>.md"}),
         ("select_by_field", {"field": "run_id", "value": b.run_id})],
        front_matter={"run_id": b.run_id},
        extra_sections=[{"heading": "Procedure card", "body": card}])

    repo0 = b.new_repo(start_repo, "ledger routing bundle")
    repo0.add_commit("import ledger bundle", {start_path: start_doc})
    b.world.add("repo", {"repo": start_repo})
    b.world.add("file", {"repo": start_repo, "path": start_path})

    routed_doc = build_instruction_markdown(
        b.rng, "routed", b.level_tag,
        [("open_repo_named", {"repo": final_repo}),
         ("final_file", {"path": terminal_path})],
        front_matter={"run_id": b.run_id})

    for code in codes:
        name = "%s_%s_%s" % (stem, gold_int, code)
        records_path = "records/%s.md" % name
        is_real = name == real_repo
        run_field = b.run_id if is_real else perturb_ref(
            b.rng, b.run_id, "cand:" + code)
        body = routed_doc if is_real else build_instruction_markdown(
            b.rng, "decoy:" + code, b.level_tag,
            [("read_file", {"path": "notes/%s_recap.md" % code})],
            front_matter={"run_id": run_field})
        if is_real:
            # rebuild with the correct run_id front matter already present
            body = routed_doc
        repo = b.new_repo(name, "series archive %s" % code)
        repo.add_commit("archive series records", {records_path: body})
        b.world.add("repo", {"repo": name},
                    decoy_status="real" if is_real else "decoy",
                    invalid_rule="" if is_real else
                    "records/%s.md run_id != %s" % (name, b.run_id),
                    source_dependencies=[gold_cache])

    repo_final = b.new_repo(final_repo, "archived rollout outputs")
    repo_final.add_commit("archive rollout outputs",
                          {terminal_path: b.terminal_file_content()})
    b.world.add("repo", {"repo": final_repo})
    b.world.add("file", {"repo": final_repo, "path": terminal_path})

    b.chain.add("github_file", {"repo": start_repo, "path": start_path},
                "github", gold_date, skill_ids=["get_gold_price"])
    b.chain.add("api_value",
                {"source": GoldPriceSource.name,
                 "query": {"symbol": "GC=F", "date": gold_date},
                 "rule": "round_nearest_integer"},
                "external_api", gold_int,
                normalization="round_nearest_integer",
                source_cache_id=gold_cache, skill_ids=["get_gold_price"])
    b.chain.add("github_repo_search",
                {"pattern": pattern, "expected_repo": real_repo,
                 "check_path": "records/{repo}.md",
                 "check_field": "run_id", "check_value": b.run_id},
                "github", real_repo,
                validation="run_id == %s" % b.run_id,
                skill_ids=["search_and_filter_repositories"])
    b.chain.add("github_file",
                {"repo": real_repo, "path": "records/%s.md" % real_repo},
                "github", "%s %s" % (final_repo, terminal_path))
    b.chain.add("terminal", {"repo": final_repo, "path": terminal_path},
                "github", b.token)

    return b.finalize(start_repo, start_path,
                      allowed_tools=["github", "external_api", "file"],
                      approved_sources=["TreasureHuntBench GitHub",
                                        GoldPriceSource.name],
                      step_budget=120)
