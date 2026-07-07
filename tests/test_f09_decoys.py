import json
import re

from thb.families import f09_decoys
from thb.gen.github_pub import LocalMirrorPublisher
from thb.gen.youtube_pub import YouTubeMirror

from families_common import assert_family_contract, grep_baseline_fails


def test_family9_generation(tmp_path):
    out = str(tmp_path / "world")
    result = f09_decoys.generate(seed=909, split="training", out_root=out,
                                 world_id="W-TEST")
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    github = LocalMirrorPublisher(out)
    mirror = YouTubeMirror(out)
    nodes = result.private_manifest.clue_nodes()
    cand = next(n for n in nodes if n.artifact_type == "youtube_candidates")

    listing = json.loads(github.read_file(cand.location["list_repo"],
                                          cand.location["list_path"]))
    refs = listing["video_refs"]
    assert len(refs) == f09_decoys.N_VIDEOS

    # exactly one video's description carries the true run_ref
    valid = [r for r in refs
             if "run_ref=%s" % cand.location["check_value"]
             in mirror.metadata(r)["description"]]
    assert valid == [cand.location["expected_ref"]]

    # decoy videos show injection bait with fake tokens, never the real one
    ts = cand.location["timestamp"]
    for ref in refs:
        lines = "\n".join(mirror.text_at(ref, ts))
        if ref == cand.location["expected_ref"]:
            assert lines == cand.observation
        else:
            assert "THB{" in lines            # fake token bait present
            assert result.token not in lines  # never the real token

    # only the active document routes to the terminal
    doc_node = nodes[2]
    active = github.read_file(doc_node.location["repo"],
                              doc_node.location["path"])
    assert "artifact_state: active" in active
    assert "run_ref: %s" % result.run_id in active
    inactive_art = next(a for a in result.private_manifest.artifacts()
                        if a.invalid_rule == "artifact_state == inactive")
    inactive = github.read_file(inactive_art.public_location["repo"],
                                inactive_art.public_location["path"])
    assert "artifact_state: inactive" in inactive
    assert nodes[3].location["path"] not in inactive

    terminal = nodes[3]
    assert github.read_file(terminal.location["repo"],
                            terminal.location["path"]).strip() == result.token


def test_family9_deterministic(tmp_path):
    a = f09_decoys.generate(51, "training", str(tmp_path / "a"), "W")
    b = f09_decoys.generate(51, "training", str(tmp_path / "b"), "W")
    assert a.token == b.token and a.notes["valid_video"] == b.notes["valid_video"]
