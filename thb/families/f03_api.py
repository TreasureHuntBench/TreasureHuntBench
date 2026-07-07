"""Level Family 3: API-Based Historical Data.

Open-Meteo historical weather drives the routing and the sub-level
introduces the ``get_coldest_hour`` skill:

start runbook (city + date) -> coldest hour (two-digit) -> hour-keyed table
row -> routed document -> terminal file in a second repository.
"""

from typing import Any, Dict, Optional

from ..artifacts.files import csv_text
from ..gen.instructions import build_instruction_markdown
from ..graphs.skills import SkillGraph, skill_card_markdown
from ..sources.base import bundle
from ..sources.open_meteo import OpenMeteoSource
from .registry import LevelBuilder, LevelResult


def bundled_weather_pairs():
    return sorted(tuple(k.split("|")) for k in bundle()["open_meteo"])


def generate(seed: int, split: str, out_root: str, world_id: str,
             sub_num: int = 1, skill_graph: Optional[SkillGraph] = None,
             world_memory: Optional[Dict[str, Any]] = None) -> LevelResult:
    b = LevelBuilder(3, sub_num, seed, split, out_root, world_id,
                     skill_graph, world_memory)

    city, date = b.rng.choice("weather_pair", bundled_weather_pairs())
    tz = "Europe/Berlin"
    hour = b.resolve_source(OpenMeteoSource(),
                            {"city": city, "date": date, "timezone": tz},
                            "coldest_hour_two_digit")
    weather_cache = b.last_cache_id()

    start_repo = b.forge.repo_name(label="start")
    second_repo = b.forge.repo_name(label="second")
    start_path = b.forge.start_path()
    table_path = b.forge.file_path("hours", ext="csv")
    routed_path = b.forge.file_path("routed")
    terminal_path = b.forge.file_path("terminal", ext="txt")

    # 24-row table keyed by two-digit hour; only the coldest hour routes on
    rows = []
    for h in range(24):
        key = "%02d" % h
        if key == hour:
            rows.append([key, routed_path])
        else:
            rows.append([key, "notes/%s_%s_recap.md"
                         % (b.level_tag, b.rng.code("hf:%02d" % h, 3))])
    table = csv_text(["hour", "document"], rows)

    b.skills.introduce("get_coldest_hour", b.level_tag, card_path=start_path)
    card = skill_card_markdown(
        "get_coldest_hour",
        inputs="city from the approved gazetteer, date, timezone",
        normalization="two-digit hour of minimum temperature; earliest on ties")

    start_doc = build_instruction_markdown(
        b.rng, "start", b.level_tag,
        [("coldest_hour_var", {"city": city, "date": date, "tz": tz,
                               "var": "HOUR_24"}),
         ("csv_row_by_var", {"path": table_path, "var": "HOUR_24"})],
        front_matter={"run_id": b.run_id},
        extra_sections=[{"heading": "Procedure card", "body": card}])
    routed_doc = build_instruction_markdown(
        b.rng, "routed", b.level_tag,
        [("open_repo_named", {"repo": second_repo}),
         ("final_file", {"path": terminal_path})],
        front_matter={"run_id": b.run_id})

    repo1 = b.new_repo(start_repo, "field measurement digests")
    repo1.add_commit("import measurement digests",
                     {start_path: start_doc, table_path: table})
    repo1.add_commit("add routed records", {routed_path: routed_doc})

    repo2 = b.new_repo(second_repo, "archived measurement outputs")
    repo2.add_commit("archive outputs",
                     {terminal_path: b.terminal_file_content()})

    for repo in (start_repo, second_repo):
        b.world.add("repo", {"repo": repo})
    for path in (start_path, table_path, routed_path):
        b.world.add("file", {"repo": start_repo, "path": path})
    b.world.add("file", {"repo": second_repo, "path": terminal_path},
                source_dependencies=[weather_cache])

    b.chain.add("github_file", {"repo": start_repo, "path": start_path},
                "github", "%s %s" % (city, date))
    b.chain.add("api_value",
                {"source": OpenMeteoSource.name,
                 "query": {"city": city, "date": date, "timezone": tz},
                 "rule": "coldest_hour_two_digit"},
                "external_api", hour,
                normalization="coldest_hour_two_digit",
                source_cache_id=weather_cache,
                skill_ids=["get_coldest_hour"])
    b.chain.add("csv_row",
                {"repo": start_repo, "path": table_path, "key": hour},
                "github", routed_path)
    b.chain.add("github_file", {"repo": start_repo, "path": routed_path},
                "github", "%s %s" % (second_repo, terminal_path))
    b.chain.add("terminal", {"repo": second_repo, "path": terminal_path},
                "github", b.token)

    return b.finalize(start_repo, start_path,
                      allowed_tools=["github", "external_api", "file"],
                      approved_sources=["TreasureHuntBench GitHub",
                                        OpenMeteoSource.name],
                      step_budget=80)
