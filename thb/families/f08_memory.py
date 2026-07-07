"""Level Family 8: Memory, Knowledge Base, and Skill Transfer.

Sub-level 1 introduces a task-specific term vocabulary (rotated per world)
and instructs the agent to store it. Sub-level 2 uses only the mapped terms:
the weather term drives a capture timestamp, the capture routes to a repository
whose document requires a git-history lookup below a named commit message.

The vocabulary travels between sub-levels through the world memory dict
(``world_memory["L8_mappings"]``); an agent must carry it in its own memory.
"""

from typing import Any, Dict, Optional

from ..artifacts.captures import build_capture_vtt
from ..gen.instructions import build_instruction_markdown
from ..graphs.skills import SkillGraph, skill_card_markdown
from ..sources.open_meteo import OpenMeteoSource
from .f03_api import bundled_weather_pairs
from .registry import LevelBuilder, LevelResult

_TERM_POOLS = {
    "weather_source": ["storm", "gale", "front", "squall"],
    "video": ["mirror", "glass", "prism", "lens"],
    "git_history": ["anchor", "keel", "mooring", "ballast"],
    "documentation": ["lantern", "beacon", "lamp", "signal"],
    "market_source": ["market", "bazaar", "exchange", "bourse"],
}

_MEANINGS = {
    "weather_source": "approved historical-weather source",
    "video": "timed capture artifact (WebVTT readout)",
    "git_history": "commit history of the current repository",
    "documentation": "documentation artifact",
    "market_source": "approved financial or gold-price source",
}

MIGRATION_MSG = "migration-complete"


def pick_terms(builder: LevelBuilder) -> Dict[str, str]:
    return {role: builder.rng.choice("term:" + role, pool)
            for role, pool in _TERM_POOLS.items()}


def _generate_intro(b: LevelBuilder) -> LevelResult:
    terms = pick_terms(b)
    b.memory["L8_mappings"] = {"ref": b.level_tag, "terms": terms}

    start_repo = b.forge.repo_name(label="start")
    start_path = b.forge.start_path()
    terminal_path = b.forge.file_path("terminal", ext="txt")

    b.skills.introduce("persistent_skill_memory", b.level_tag,
                       card_path=start_path)
    card = skill_card_markdown(
        "persistent_skill_memory",
        inputs="term mappings and procedures marked for storage",
        normalization="later tasks use stored terms without redefinition")

    mapping_lines = "\n".join(
        "%s = %s" % (terms[role], _MEANINGS[role]) for role in sorted(terms))
    start_doc = build_instruction_markdown(
        b.rng, "start", b.level_tag,
        [("store_mappings", {}),
         ("final_file", {"path": terminal_path})],
        front_matter={"run_id": b.run_id},
        extra_sections=[
            {"heading": "Mappings", "body": mapping_lines},
            {"heading": "Procedure card", "body": card}])

    repo = b.new_repo(start_repo, "world vocabulary bundle")
    repo.add_commit("import vocabulary bundle",
                    {start_path: start_doc,
                     terminal_path: b.terminal_file_content()})

    b.world.add("repo", {"repo": start_repo})
    b.world.add("file", {"repo": start_repo, "path": start_path},
                skill_dependencies=["persistent_skill_memory"])
    b.world.add("file", {"repo": start_repo, "path": terminal_path})

    b.chain.add("github_file", {"repo": start_repo, "path": start_path},
                "github", terms["weather_source"],
                skill_ids=["persistent_skill_memory"])
    b.chain.add("terminal", {"repo": start_repo, "path": terminal_path},
                "github", b.token)

    return b.finalize(start_repo, start_path,
                      allowed_tools=["github", "memory", "file"],
                      approved_sources=["TreasureHuntBench GitHub"],
                      step_budget=40,
                      notes={"terms": terms})


def _generate_transfer(b: LevelBuilder) -> LevelResult:
    mappings = b.memory.get("L8_mappings")
    if not mappings:
        raise ValueError("sub-level 2 requires L8_mappings in world memory "
                         "(generate sub-level 1 first)")
    terms = mappings["terms"]
    intro_ref = mappings["ref"]

    city, date = b.rng.choice("weather_pair", bundled_weather_pairs())
    tz = "Europe/Berlin"
    hour = b.resolve_source(OpenMeteoSource(),
                            {"city": city, "date": date, "timezone": tz},
                            "coldest_hour_two_digit")
    weather_cache = b.last_cache_id()
    t = int(hour)

    start_repo = b.forge.repo_name(label="start")
    target_repo = b.forge.repo_name(label="target")
    start_path = b.forge.start_path()
    capture_path = "media/%s_readout_%s.vtt" % (
        b.level_tag, b.rng.code("cap", 3))
    routed_path = b.forge.file_path("routed")
    history_path = b.forge.file_path("ledger")
    terminal_path = b.forge.file_path("terminal", ext="txt")

    clue_lines = ["repository=%s" % target_repo,
                  "document=%s" % routed_path]
    segments = ([(0, t, ["series calibration"])] if t > 0 else [])
    segments.append((t, t + 1, clue_lines))
    segments.append((t + 1, t + 8, ["archive readout complete"]))
    capture = build_capture_vtt({"run_ref": b.run_id,
                                 "kind": "ledger readout"}, segments)

    b.skills.require("persistent_skill_memory", b.level_tag)
    b.skills.introduce("git_history_investigation", b.level_tag,
                       card_path=routed_path)
    for sid in ("get_coldest_hour", "timestamped_video_clue_extraction"):
        if sid in b.skills.skills:
            b.skills.practice(sid, b.level_tag)
        else:
            b.skills.introduce(sid, b.level_tag)

    start_doc = build_instruction_markdown(
        b.rng, "start", b.level_tag,
        [("use_mappings", {"ref": intro_ref}),
         ("mapped_weather_var", {"term": terms["weather_source"],
                                 "city": city, "date": date, "tz": tz,
                                 "var": "HOUR_24"}),
         ("mapped_open_video", {"term": terms["video"],
                                "path": capture_path}),
         ("mapped_inspect_video", {"term": terms["video"],
                                   "var": "{HOUR_24}"})],
        front_matter={"run_id": b.run_id})
    card = skill_card_markdown(
        "git_history_investigation",
        inputs="repository, anchor commit message, file path",
        normalization="the last commit strictly before the named commit")
    routed_doc = build_instruction_markdown(
        b.rng, "routed", b.level_tag,
        [("use_mappings", {"ref": intro_ref}),
         ("mapped_git_before", {"term": terms["git_history"],
                                "msg": MIGRATION_MSG,
                                "path": history_path})],
        front_matter={"run_id": b.run_id},
        extra_sections=[{"heading": "Procedure card", "body": card}])
    payload_doc = build_instruction_markdown(
        b.rng, "payload", b.level_tag,
        [("final_file", {"path": terminal_path})],
        front_matter={"run_id": b.run_id})

    repo1 = b.new_repo(start_repo, "ledger readout bundle")
    repo1.add_commit("import readout bundle",
                     {start_path: start_doc, capture_path: capture})

    repo2 = b.new_repo(target_repo, "ledger archive")
    repo2.add_commit("field records import",
                     {history_path: payload_doc,
                      "notes/%s_scope.md" % b.level_tag: "# scope\n"})
    repo2.add_commit("pre-rollout adjustments",
                     {"notes/%s_scope.md" % b.level_tag:
                      "# scope\nadjusted before rollout\n"})
    repo2.add_commit(MIGRATION_MSG,
                     {history_path:
                      "# migrated\nContent moved during migration.\n"})
    repo2.add_commit("post-migration cleanup",
                     {routed_path: routed_doc,
                      terminal_path: b.terminal_file_content()})

    for repo in (start_repo, target_repo):
        b.world.add("repo", {"repo": repo})
    b.world.add("file", {"repo": start_repo, "path": start_path},
                skill_dependencies=["persistent_skill_memory"])
    b.world.add("file", {"repo": start_repo, "path": capture_path},
                source_dependencies=[weather_cache])
    b.world.add("file", {"repo": target_repo, "path": routed_path},
                skill_dependencies=["git_history_investigation"])
    b.world.add("file", {"repo": target_repo, "path": terminal_path})

    b.chain.add("github_file", {"repo": start_repo, "path": start_path},
                "github", capture_path,
                skill_ids=["persistent_skill_memory"])
    b.chain.add("api_value",
                {"source": OpenMeteoSource.name,
                 "query": {"city": city, "date": date, "timezone": tz},
                 "rule": "coldest_hour_two_digit"},
                "external_api", hour,
                normalization="coldest_hour_two_digit",
                source_cache_id=weather_cache,
                skill_ids=["get_coldest_hour"])
    b.chain.add("vtt_timestamp",
                {"repo": start_repo, "path": capture_path,
                 "timestamp": "00:%s" % hour},
                "file", "\n".join(clue_lines),
                skill_ids=["timestamped_video_clue_extraction"])
    b.chain.add("github_file", {"repo": target_repo, "path": routed_path},
                "github", MIGRATION_MSG,
                skill_ids=["persistent_skill_memory"])
    b.chain.add("git_history",
                {"repo": target_repo, "before_message": MIGRATION_MSG,
                 "path": history_path},
                "github", terminal_path,
                skill_ids=["git_history_investigation"])
    b.chain.add("terminal", {"repo": target_repo, "path": terminal_path},
                "github", b.token)

    return b.finalize(start_repo, start_path,
                      allowed_tools=["github", "external_api",
                                     "memory", "file"],
                      approved_sources=["TreasureHuntBench GitHub",
                                        OpenMeteoSource.name],
                      step_budget=150,
                      notes={"terms": terms})


def generate(seed: int, split: str, out_root: str, world_id: str,
             sub_num: int = 1, skill_graph: Optional[SkillGraph] = None,
             world_memory: Optional[Dict[str, Any]] = None) -> LevelResult:
    b = LevelBuilder(8, sub_num, seed, split, out_root, world_id,
                     skill_graph, world_memory)
    if sub_num == 1:
        return _generate_intro(b)
    return _generate_transfer(b)
