"""Level Family 7: Encoded and Hidden Message Extraction (video-free).

Introduces ``decode_explicit_hidden_messages``: the first characters of the
last five entry titles of an in-repo upload log, decoded with a stated
Caesar shift, yield the tag that names the next repository and its route
document.
"""

import string
from typing import Any, Dict, Optional

from ..artifacts.captures import build_upload_log
from ..artifacts.encodings import caesar_decode, caesar_encode
from ..gen.instructions import build_instruction_markdown
from ..graphs.skills import SkillGraph, skill_card_markdown
from .registry import LevelBuilder, LevelResult

SHIFT = 5
_FILLERS = ["ite survey notes", "arly figures", "vent recap",
            "eries calibration", "rchive walkthrough", "olling averages",
            "atch summary", "udit extract", "ield diary", "rder ledger"]


def generate(seed: int, split: str, out_root: str, world_id: str,
             sub_num: int = 1, skill_graph: Optional[SkillGraph] = None,
             world_memory: Optional[Dict[str, Any]] = None) -> LevelResult:
    b = LevelBuilder(7, sub_num, seed, split, out_root, world_id,
                     skill_graph, world_memory)

    tag = b.rng.code("decoded_tag", 5, string.ascii_uppercase)
    encoded = caesar_encode(tag, SHIFT)
    assert caesar_decode(encoded, SHIFT) == tag

    start_repo = b.forge.repo_name(label="start")
    tagged_repo = "%s-%s-%s" % (b.forge.repo_stem(), b.level_tag, tag)
    start_path = b.forge.start_path()
    log_path = "media/%s_uploads_%s.json" % (b.level_tag,
                                             b.rng.code("plref", 3))
    route_path = "packets/%s_route.md" % tag
    terminal_path = b.forge.file_path("terminal", ext="txt")

    # upload log: two filler entries then five whose first chars spell
    # `encoded`
    fillers = b.rng.sample("fillers", _FILLERS, 7)
    titles = [fillers[0].capitalize(), fillers[1].capitalize()]
    for ch, filler in zip(encoded, fillers[2:]):
        titles.append(ch + filler)
    upload_log = build_upload_log(titles)

    b.skills.introduce("decode_explicit_hidden_messages", b.level_tag,
                       card_path=start_path)
    card = skill_card_markdown(
        "decode_explicit_hidden_messages",
        inputs="component specification (which characters, which order), "
               "decoding method and parameters",
        normalization="exactly one decoded output is valid")

    start_doc = build_instruction_markdown(
        b.rng, "start", b.level_tag,
        [("list_last_titles", {"path": log_path, "n": 5}),
         ("first_chars_var", {"var": "RAW_TAG"}),
         ("decode_caesar_var", {"value": "RAW_TAG", "shift": SHIFT,
                                "var": "ROUTE_TAG"}),
         ("open_repo_named",
          {"repo": "%s-%s-{ROUTE_TAG}" % (tagged_repo.rsplit("-", 1)[0]
                                          .split("-")[0], b.level_tag)}),
         ("read_file", {"path": "packets/{ROUTE_TAG}_route.md"})],
        front_matter={"run_id": b.run_id},
        extra_sections=[{"heading": "Procedure card", "body": card}])
    route_doc = build_instruction_markdown(
        b.rng, "route", b.level_tag,
        [("final_file", {"path": terminal_path})],
        front_matter={"run_id": b.run_id})

    repo1 = b.new_repo(start_repo, "upload processing bundle")
    repo1.add_commit("import upload bundle",
                     {start_path: start_doc, log_path: upload_log})
    repo2 = b.new_repo(tagged_repo, "routed packet archive")
    repo2.add_commit("archive routed packets",
                     {route_path: route_doc,
                      terminal_path: b.terminal_file_content()})

    for repo in (start_repo, tagged_repo):
        b.world.add("repo", {"repo": repo})
    b.world.add("file", {"repo": start_repo, "path": start_path})
    b.world.add("file", {"repo": start_repo, "path": log_path})
    b.world.add("file", {"repo": tagged_repo, "path": route_path})
    b.world.add("file", {"repo": tagged_repo, "path": terminal_path})

    b.chain.add("github_file", {"repo": start_repo, "path": start_path},
                "github", log_path)
    b.chain.add("titles_list",
                {"repo": start_repo, "path": log_path, "last_n": 5,
                 "method": "caesar", "shift": SHIFT},
                "file", tag,
                normalization="first characters of last 5 titles, Caesar "
                              "shift %d" % SHIFT,
                skill_ids=["decode_explicit_hidden_messages"])
    b.chain.add("github_file", {"repo": tagged_repo, "path": route_path},
                "github", terminal_path)
    b.chain.add("terminal", {"repo": tagged_repo, "path": terminal_path},
                "github", b.token)

    return b.finalize(start_repo, start_path,
                      allowed_tools=["github", "python", "file"],
                      approved_sources=["TreasureHuntBench GitHub"],
                      step_budget=100)
