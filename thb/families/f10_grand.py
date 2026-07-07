"""Level Family 10: Grand Multi-Source Hunt.

Composes every previously introduced skill into one long deterministic
investigation:

start runbook (mapped terms) -> event record (city/date + mirror ref) ->
coldest hour -> video timestamp showing market fields -> gold close ->
MARKET_KEY -> repository search with manifest validation (run_ref +
artifact_state) -> German documentation artifact -> git history below
"migration-complete" -> Caesar-encoded branch name -> branch CSV row keyed
by MARKET_KEY -> password-protected ZIP -> Arabic document -> terminal file.
"""

import json
import string
from typing import Any, Dict, Optional

from ..artifacts.archive import write_zip
from ..artifacts.encodings import caesar_encode
from ..artifacts.files import csv_text
from ..gen.decoys import decoy_state_fields, near_duplicate_keys
from ..gen.instructions import build_instruction_markdown
from ..gen.youtube_pub import Segment, VideoSpec, video_reference_file
from ..graphs.skills import SkillGraph
from ..sources.gold import GoldPriceSource, bundled_gold_dates
from ..sources.open_meteo import OpenMeteoSource
from .f03_api import bundled_weather_pairs
from .f08_memory import MIGRATION_MSG
from .registry import LevelBuilder, LevelResult

SHIFT = 7
N_CANDIDATES = 3

REQUIRED_SKILLS = [
    "get_gold_price", "get_coldest_hour", "search_and_filter_repositories",
    "timestamped_video_clue_extraction", "cross_lingual_clue_following",
    "decode_explicit_hidden_messages", "persistent_skill_memory",
    "verify_before_following", "git_history_investigation",
    "source_citation_and_provenance",
]


def generate(seed: int, split: str, out_root: str, world_id: str,
             sub_num: int = 1, skill_graph: Optional[SkillGraph] = None,
             world_memory: Optional[Dict[str, Any]] = None) -> LevelResult:
    b = LevelBuilder(10, sub_num, seed, split, out_root, world_id,
                     skill_graph, world_memory)

    mappings = b.memory.get("L8_mappings")
    if not mappings:
        raise ValueError("family 10 requires L8_mappings in world memory")
    terms = mappings["terms"]
    for sid in REQUIRED_SKILLS:
        if sid in b.skills.skills:
            b.skills.require(sid, b.level_tag)
        else:
            b.skills.introduce(sid, b.level_tag)

    # ---- external values --------------------------------------------------
    city, date = b.rng.choice("weather_pair", bundled_weather_pairs())
    tz = "Europe/Berlin"
    hour = b.resolve_source(OpenMeteoSource(),
                            {"city": city, "date": date, "timezone": tz},
                            "coldest_hour_two_digit")
    weather_cache = b.last_cache_id()
    t = int(hour)

    gold_date = b.rng.choice("gold_date", bundled_gold_dates())
    market_key = b.resolve_source(GoldPriceSource(),
                                  {"symbol": "GC=F", "date": gold_date},
                                  "round_nearest_integer")
    gold_cache = b.last_cache_id()

    # ---- names ------------------------------------------------------------
    start_repo = b.forge.repo_name(label="start")
    stem = b.forge.repo_stem()
    pattern = "%s-%s-%s-*" % (stem, b.level_tag, market_key)
    codes = [b.rng.code("cand:%d" % i, 2) for i in range(N_CANDIDATES)]
    real_code = b.rng.choice("real_code", codes)
    real_repo = "%s-%s-%s-%s" % (stem, b.level_tag, market_key, real_code)

    start_path = "runbooks/%s_start_%s.md" % (
        b.level_tag, b.run_id.split("-")[1])
    event_path = "records/%s_event_%s.md" % (
        b.level_tag, b.rng.code("event", 3))
    mirror_ref_path = "media/%s_mirror_%s.json" % (
        b.level_tag, b.rng.code("mref", 3))
    video_ref = "video_%s_%s" % (b.level_tag, b.rng.code("vid", 3))
    de_path = "language_pack/%s_de_%s.md" % (b.level_tag,
                                             b.rng.code("de", 4))
    hist_path = b.forge.file_path("ledger")
    branch_word = b.rng.choice("branch_word", ["series", "rollout", "ingest"])
    branch_tag = b.rng.code("branch_tag", 5, string.ascii_uppercase)
    branch = "%s-%s" % (branch_word, branch_tag)
    encoded_branch = caesar_encode(branch, SHIFT)
    table_path = "tables/%s_index_%s.csv" % (b.level_tag, market_key)
    zip_name = "packets/bundle_%s_%s.zip" % (b.level_tag,
                                             b.rng.code("zip", 3))
    zip_key = "k%s-%s" % (b.rng.code("zk1", 2).lower(), market_key)
    ar_arcname = "briefs/%s_%s_ar.md" % (b.level_tag, b.run_id.split("-")[1])
    terminal_path = b.forge.file_path("terminal", ext="txt")

    # ---- video: market fields at the weather-derived second ---------------
    clue_lines = ["series_id=GC=F",
                  "observation_date=%s" % gold_date,
                  "rounding_rule=round_nearest_integer"]
    segments = [Segment(0, t, ["ledger calibration"])] if t > 0 else []
    segments.append(Segment(t, t + 1, clue_lines))
    segments.append(Segment(t + 1, t + 8, ["ledger readout complete"]))
    b.youtube.build_video(VideoSpec(
        ref=video_ref,
        title="%s ledger capture %s" % (b.level_tag, b.rng.code("vt", 3)),
        description="run_ref=%s\narchived ledger capture" % b.run_id,
        segments=segments))

    # ---- documents ---------------------------------------------------------
    start_doc = build_instruction_markdown(
        b.rng, "start", b.level_tag,
        [("use_mappings", {"ref": mappings["ref"]}),
         ("read_file", {"path": event_path})],
        front_matter={"run_id": b.run_id})
    event_doc = build_instruction_markdown(
        b.rng, "event", b.level_tag,
        [("mapped_weather_var", {"term": terms["weather_source"],
                                 "city": city, "date": date, "tz": tz,
                                 "var": "HOUR_24"}),
         ("mapped_open_video", {"term": terms["video"],
                                "path": mirror_ref_path}),
         ("mapped_inspect_video", {"term": terms["video"],
                                   "var": "{HOUR_24}"}),
         ("round_nearest_var", {"var": "MARKET_KEY"}),
         ("search_repos_pattern",
          {"pattern": "%s-%s-{MARKET_KEY}-*" % (stem, b.level_tag)}),
         ("read_candidates", {"path_template": "manifests/<repository>.json"}),
         ("select_by_field", {"field": "run_ref and artifact_state",
                              "value": "%s / active" % b.run_id})],
        front_matter={"run_id": b.run_id})
    de_doc = build_instruction_markdown(
        b.rng, "lantern", b.level_tag,
        [("translate_and_execute", {}),
         ("mapped_git_before", {"term": terms["git_history"],
                                "msg": MIGRATION_MSG, "path": hist_path})],
        lang="de", front_matter={"run_id": b.run_id})
    hist_doc = build_instruction_markdown(
        b.rng, "histpayload", b.level_tag,
        [("decode_caesar_var", {"value": encoded_branch, "shift": SHIFT,
                                "var": "BRANCH_REF"}),
         ("open_branch", {"branch": "{BRANCH_REF}"}),
         ("csv_row_by_var", {"path": table_path, "var": "MARKET_KEY"})],
        front_matter={"run_id": b.run_id})
    ar_doc = build_instruction_markdown(
        b.rng, "arabic", b.level_tag,
        [("translate_and_execute", {}),
         ("final_file", {"path": terminal_path})],
        lang="ar", front_matter={"run_id": b.run_id})

    # ---- branch CSV keyed by MARKET_KEY ------------------------------------
    rows = [[market_key, zip_name, zip_key]]
    for near in near_duplicate_keys(b.rng, int(market_key), 5):
        rows.append([str(near),
                     "packets/bundle_%s_%s.zip"
                     % (b.level_tag, b.rng.code("zf:%d" % near, 3)),
                     "k%s-%d" % (b.rng.code("zk:%d" % near, 2).lower(), near)])
    rows = b.rng.shuffle("row_order", rows)
    table = ("# key column: MARKET_KEY; matching row gives archive_file and "
             "archive_key\n" + csv_text(
                 ["market_key", "archive_file", "archive_key"], rows))

    zip_bytes_path = write_zip(
        "%s/tmp_%s.zip" % (out_root, b.rng.code("ztmp", 4)),
        {ar_arcname: ar_doc}, password=zip_key)
    with open(zip_bytes_path, "rb") as fh:
        zip_bytes = fh.read()
    import os
    os.remove(zip_bytes_path)

    # ---- repositories -------------------------------------------------------
    repo1 = b.new_repo(start_repo, "grand ledger bundle")
    repo1.add_commit("import ledger bundle", {
        start_path: start_doc,
        event_path: event_doc,
        mirror_ref_path: json.dumps(video_reference_file(video_ref),
                                    indent=2) + "\n"})
    b.world.add("repo", {"repo": start_repo})
    b.world.add("video", {"video_ref": video_ref},
                source_dependencies=[weather_cache])

    for code in codes:
        name = "%s-%s-%s-%s" % (stem, b.level_tag, market_key, code)
        is_real = name == real_repo
        if is_real:
            fields = decoy_state_fields(b.run_id, b.rng, code, "valid")
        else:
            mode = b.rng.choice("decoy_mode:" + code,
                                ["wrong_ref", "inactive"])
            fields = decoy_state_fields(b.run_id, b.rng, code, mode)
        manifest = dict(fields, document=de_path)
        repo = b.new_repo(name, "ledger archive %s" % code)
        commits = {("manifests/%s.json" % name):
                   json.dumps(manifest, indent=2, sort_keys=True) + "\n"}
        if is_real:
            repo.add_commit("field records import", dict(
                commits, **{hist_path: hist_doc, de_path: de_doc}))
            repo.add_commit("pre-rollout adjustments",
                            {"notes/%s_scope.md" % b.level_tag:
                             "# scope\nadjusted\n"})
            repo.add_commit(MIGRATION_MSG,
                            {hist_path: "# migrated\nContent moved.\n"})
            repo.add_commit("post-migration cleanup",
                            {"notes/%s_post.md" % b.level_tag: "# post\n"})
            repo.add_commit("archive branch tables",
                            {table_path: table,
                             zip_name: zip_bytes,
                             terminal_path: b.terminal_file_content()},
                            branch=branch)
        else:
            repo.add_commit("field records import", dict(
                commits, **{de_path: "# archiv\nKein aktiver Bestand.\n"}))
        b.world.add("repo", {"repo": name},
                    decoy_status="real" if is_real else "decoy",
                    invalid_rule="" if is_real else
                    "manifest run_ref/artifact_state check fails",
                    source_dependencies=[gold_cache])

    # ---- clue chain ---------------------------------------------------------
    b.chain.add("github_file", {"repo": start_repo, "path": start_path},
                "github", event_path,
                skill_ids=["persistent_skill_memory"])
    b.chain.add("github_file", {"repo": start_repo, "path": event_path},
                "github", mirror_ref_path)
    b.chain.add("api_value",
                {"source": OpenMeteoSource.name,
                 "query": {"city": city, "date": date, "timezone": tz},
                 "rule": "coldest_hour_two_digit"},
                "external_api", hour,
                normalization="coldest_hour_two_digit",
                source_cache_id=weather_cache,
                skill_ids=["get_coldest_hour"])
    b.chain.add("youtube_timestamp",
                {"video_ref": video_ref, "timestamp": "00:%s" % hour},
                "youtube", "\n".join(clue_lines),
                skill_ids=["timestamped_video_clue_extraction"])
    b.chain.add("api_value",
                {"source": GoldPriceSource.name,
                 "query": {"symbol": "GC=F", "date": gold_date},
                 "rule": "round_nearest_integer"},
                "external_api", market_key,
                normalization="round_nearest_integer",
                source_cache_id=gold_cache, skill_ids=["get_gold_price"])
    b.chain.add("github_repo_search",
                {"pattern": pattern, "expected_repo": real_repo,
                 "check_path": "manifests/{repo}.json",
                 "check_field": "run_ref", "check_value": b.run_id,
                 "check2_field": "artifact_state", "check2_value": "active"},
                "github", real_repo,
                validation="run_ref == %s and artifact_state == active"
                           % b.run_id,
                skill_ids=["search_and_filter_repositories",
                           "verify_before_following"])
    b.chain.add("github_file", {"repo": real_repo, "path": de_path},
                "github", MIGRATION_MSG,
                skill_ids=["cross_lingual_clue_following"])
    b.chain.add("git_history",
                {"repo": real_repo, "before_message": MIGRATION_MSG,
                 "path": hist_path},
                "github", encoded_branch,
                normalization="caesar shift %d decode -> branch name" % SHIFT,
                skill_ids=["git_history_investigation",
                           "decode_explicit_hidden_messages"])
    b.chain.add("csv_row",
                {"repo": real_repo, "path": table_path, "branch": branch,
                 "key": market_key},
                "github", "%s %s" % (zip_name, zip_key))
    b.chain.add("zip_entry",
                {"repo": real_repo, "path": zip_name, "branch": branch,
                 "arcname": ar_arcname, "password": zip_key},
                "archive", terminal_path,
                skill_ids=["cross_lingual_clue_following"])
    b.chain.add("terminal",
                {"repo": real_repo, "path": terminal_path, "branch": branch},
                "github", b.token)

    return b.finalize(start_repo, start_path,
                      allowed_tools=["github", "youtube", "external_api",
                                     "python", "archive", "translation",
                                     "memory", "file"],
                      approved_sources=["TreasureHuntBench GitHub",
                                        "TreasureHuntBench YouTube",
                                        OpenMeteoSource.name,
                                        GoldPriceSource.name],
                      step_budget=400,
                      notes={"terms": terms, "branch": branch,
                             "market_key": market_key})
