"""Level Family 2: Real-Website Navigation.

Wikipedia/Wikidata provide intermediate routing values and the sub-level
introduces the ``get_gold_price`` skill (with a stored skill card):

start runbook (city page) -> Wikipedia wikibase item (QID) -> QID-keyed CSV
row -> skill document (gold price for a date) -> gold-keyed repository ->
terminal file.
"""

from typing import Any, Dict, Optional

from ..artifacts.files import csv_text
from ..gen.instructions import build_instruction_markdown
from ..graphs.skills import SkillGraph, skill_card_markdown
from ..sources.gold import GoldPriceSource, bundled_gold_dates
from ..sources.wiki import WikipediaSummarySource, city_qid
from ..sources.open_meteo import approved_cities
from .registry import LevelBuilder, LevelResult


def generate(seed: int, split: str, out_root: str, world_id: str,
             sub_num: int = 1, skill_graph: Optional[SkillGraph] = None,
             world_memory: Optional[Dict[str, Any]] = None) -> LevelResult:
    b = LevelBuilder(2, sub_num, seed, split, out_root, world_id,
                     skill_graph, world_memory)

    city = b.rng.choice("city", approved_cities())
    page = city.split(",")[0].strip()
    qid = b.resolve_source(WikipediaSummarySource(),
                           {"page": page, "field": "wikibase_item"},
                           "verbatim")
    wiki_cache = b.last_cache_id()

    gold_date = b.rng.choice("gold_date", bundled_gold_dates())
    gold_int = b.resolve_source(GoldPriceSource(),
                                {"symbol": "GC=F", "date": gold_date},
                                "round_nearest_integer")
    gold_cache = b.last_cache_id()

    start_repo = b.forge.repo_name(label="start")
    keyed_repo = b.forge.repo_name(key=gold_int, label="gold")
    start_path = b.forge.start_path()
    table_path = b.forge.file_path("routing", ext="csv")
    skill_path = b.forge.file_path("skilldoc")
    terminal_path = b.forge.file_path("terminal", ext="txt")

    # QID-keyed routing table (filler rows use other cities' QIDs)
    other_qids = [city_qid(c) for c in approved_cities() if c != city]
    rows = [[qid, skill_path]]
    for extra_qid in b.rng.sample("filler_qids", other_qids, 6):
        rows.append([extra_qid,
                     "notes/%s_%s_recap.md"
                     % (b.level_tag, b.rng.code("fq:" + extra_qid, 3))])
    rows = b.rng.shuffle("row_order", rows)
    table = csv_text(["item_id", "document"], rows)

    start_doc = build_instruction_markdown(
        b.rng, "start", b.level_tag,
        [("wiki_item_var", {"page": page, "var": "ITEM_ID"}),
         ("csv_row_by_var", {"path": table_path, "var": "ITEM_ID"})],
        front_matter={"run_id": b.run_id})

    b.skills.introduce("get_gold_price", b.level_tag, card_path=skill_path)
    b.skills.introduce("source_citation_and_provenance", b.level_tag,
                       card_path=skill_path)
    card = skill_card_markdown(
        "get_gold_price",
        inputs="trading date (YYYY-MM-DD); source: Yahoo Finance GC=F daily close, USD",
        normalization="round to nearest integer unless a task states otherwise")
    skill_doc = build_instruction_markdown(
        b.rng, "skill", b.level_tag,
        [("use_gold_source", {}),
         ("get_gold_for_date", {"date": gold_date}),
         ("round_nearest_var", {"var": "GOLD_INT"}),
         ("open_repo_named", {"repo": keyed_repo.replace(gold_int, "{GOLD_INT}")}),
         ("final_file", {"path": terminal_path})],
        front_matter={"run_id": b.run_id},
        extra_sections=[{"heading": "Procedure card", "body": card},
                        {"heading": "Recording",
                         "body": ("For every external value used, record the "
                                  "source, the exact query, the retrieved "
                                  "value, and the rule applied.")}])

    repo1 = b.new_repo(start_repo, "survey routing bundle")
    repo1.add_commit("import survey bundle",
                     {start_path: start_doc, table_path: table})
    repo1.add_commit("add procedure records", {skill_path: skill_doc})

    repo2 = b.new_repo(keyed_repo, "archived series outputs")
    repo2.add_commit("archive series outputs",
                     {terminal_path: b.terminal_file_content(),
                      "notes/%s_series_scope.md" % b.level_tag:
                      "# scope\nSeries archive for batch %s.\n"
                      % b.rng.code("scope", 3)})

    for repo in (start_repo, keyed_repo):
        b.world.add("repo", {"repo": repo})
    b.world.add("file", {"repo": start_repo, "path": start_path})
    b.world.add("file", {"repo": start_repo, "path": table_path})
    b.world.add("file", {"repo": start_repo, "path": skill_path},
                skill_dependencies=["get_gold_price"])
    b.world.add("file", {"repo": keyed_repo, "path": terminal_path},
                source_dependencies=[gold_cache])

    b.chain.add("github_file", {"repo": start_repo, "path": start_path},
                "github", page)
    b.chain.add("api_value",
                {"source": WikipediaSummarySource.name,
                 "query": {"page": page, "field": "wikibase_item"},
                 "rule": "verbatim"},
                "external_api", qid, normalization="verbatim",
                source_cache_id=wiki_cache,
                skill_ids=["source_citation_and_provenance"])
    b.chain.add("csv_row",
                {"repo": start_repo, "path": table_path, "key": qid},
                "github", skill_path)
    b.chain.add("github_file", {"repo": start_repo, "path": skill_path},
                "github", gold_date, skill_ids=["get_gold_price"])
    b.chain.add("api_value",
                {"source": GoldPriceSource.name,
                 "query": {"symbol": "GC=F", "date": gold_date},
                 "rule": "round_nearest_integer"},
                "external_api", gold_int,
                normalization="round_nearest_integer",
                source_cache_id=gold_cache, skill_ids=["get_gold_price"])
    b.chain.add("terminal", {"repo": keyed_repo, "path": terminal_path},
                "github", b.token)

    return b.finalize(start_repo, start_path,
                      allowed_tools=["github", "browser", "external_api",
                                     "file"],
                      approved_sources=[
                          "TreasureHuntBench GitHub",
                          "Wikipedia REST page summary",
                          GoldPriceSource.name],
                      step_budget=80)
