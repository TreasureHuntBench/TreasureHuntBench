"""Level Family 5: YouTube Timestamp and Metadata Clues.

Reuses ``get_coldest_hour`` and introduces
``timestamped_video_clue_extraction``: the coldest hour becomes a video
timestamp (``00:HH`` = HH seconds); the frame/caption at that timestamp
displays the next repository and document as structured fields.
"""

import json
from typing import Any, Dict, Optional

from ..gen.instructions import build_instruction_markdown
from ..gen.youtube_pub import Segment, VideoSpec, video_reference_file
from ..graphs.skills import SkillGraph, skill_card_markdown
from ..sources.open_meteo import OpenMeteoSource
from .f03_api import bundled_weather_pairs
from .registry import LevelBuilder, LevelResult


def generate(seed: int, split: str, out_root: str, world_id: str,
             sub_num: int = 1, skill_graph: Optional[SkillGraph] = None,
             world_memory: Optional[Dict[str, Any]] = None) -> LevelResult:
    b = LevelBuilder(5, sub_num, seed, split, out_root, world_id,
                     skill_graph, world_memory)

    city, date = b.rng.choice("weather_pair", bundled_weather_pairs())
    tz = "Europe/Berlin"
    hour = b.resolve_source(OpenMeteoSource(),
                            {"city": city, "date": date, "timezone": tz},
                            "coldest_hour_two_digit")
    weather_cache = b.last_cache_id()
    t = int(hour)
    timestamp = "00:%s" % hour

    start_repo = b.forge.repo_name(label="start")
    routed_repo = b.forge.repo_name(label="routed")
    start_path = b.forge.start_path()
    video_ref_path = "media/%s_video_ref_%s.json" % (
        b.level_tag, b.rng.code("vref", 3))
    routed_path = b.forge.file_path("routed")
    terminal_path = b.forge.file_path("terminal", ext="txt")
    video_ref = "video_%s_%s" % (b.level_tag, b.rng.code("vid", 3))

    clue_lines = ["repository=%s" % routed_repo,
                  "document=%s" % routed_path]
    segments = [Segment(0, t, ["series calibration"])] if t > 0 else []
    segments.append(Segment(t, t + 1, clue_lines))
    segments.append(Segment(t + 1, t + 8, ["archive readout complete"]))
    video = VideoSpec(
        ref=video_ref,
        title="%s series readout %s" % (b.level_tag, b.rng.code("vt", 3)),
        description="run_ref=%s\narchived measurement readout" % b.run_id,
        segments=segments)
    b.youtube.build_video(video)

    if "get_coldest_hour" not in b.skills.skills:
        b.skills.introduce("get_coldest_hour", b.level_tag)
    else:
        b.skills.practice("get_coldest_hour", b.level_tag)
    b.skills.introduce("timestamped_video_clue_extraction", b.level_tag,
                       card_path=start_path)
    card = skill_card_markdown(
        "timestamped_video_clue_extraction",
        inputs="video reference file, derived two-digit value as 00:VALUE",
        normalization="read the structured key=value fields shown at the "
                      "timestamp")

    start_doc = build_instruction_markdown(
        b.rng, "start", b.level_tag,
        [("coldest_hour_var", {"city": city, "date": date, "tz": tz,
                               "var": "HOUR_24"}),
         ("open_video_ref", {"path": video_ref_path}),
         ("inspect_timestamp", {"var": "{HOUR_24}"})],
        front_matter={"run_id": b.run_id},
        extra_sections=[{"heading": "Procedure card", "body": card}])
    routed_doc = build_instruction_markdown(
        b.rng, "routed", b.level_tag,
        [("final_file", {"path": terminal_path})],
        front_matter={"run_id": b.run_id})

    repo1 = b.new_repo(start_repo, "measurement readout bundle")
    repo1.add_commit("import readout bundle", {
        start_path: start_doc,
        video_ref_path: json.dumps(video_reference_file(video_ref),
                                   indent=2) + "\n"})
    repo2 = b.new_repo(routed_repo, "archived readout outputs")
    repo2.add_commit("archive readout outputs",
                     {routed_path: routed_doc,
                      terminal_path: b.terminal_file_content()})

    for repo in (start_repo, routed_repo):
        b.world.add("repo", {"repo": repo})
    b.world.add("file", {"repo": start_repo, "path": start_path})
    b.world.add("file", {"repo": start_repo, "path": video_ref_path})
    b.world.add("video", {"video_ref": video_ref},
                source_dependencies=[weather_cache])
    b.world.add("file", {"repo": routed_repo, "path": terminal_path})

    b.chain.add("github_file", {"repo": start_repo, "path": start_path},
                "github", video_ref_path)
    b.chain.add("api_value",
                {"source": OpenMeteoSource.name,
                 "query": {"city": city, "date": date, "timezone": tz},
                 "rule": "coldest_hour_two_digit"},
                "external_api", hour,
                normalization="coldest_hour_two_digit",
                source_cache_id=weather_cache,
                skill_ids=["get_coldest_hour"])
    b.chain.add("youtube_timestamp",
                {"video_ref": video_ref, "timestamp": timestamp},
                "youtube", "\n".join(clue_lines),
                skill_ids=["timestamped_video_clue_extraction"])
    b.chain.add("github_file", {"repo": routed_repo, "path": routed_path},
                "github", terminal_path)
    b.chain.add("terminal", {"repo": routed_repo, "path": terminal_path},
                "github", b.token)

    return b.finalize(start_repo, start_path,
                      allowed_tools=["github", "youtube", "external_api",
                                     "file"],
                      approved_sources=["TreasureHuntBench GitHub",
                                        "TreasureHuntBench YouTube",
                                        OpenMeteoSource.name],
                      step_budget=100)
