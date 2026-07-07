import json

from thb.artifacts.captures import cue_lines_at, parse_note_fields
from thb.families import f09_decoys
from thb.gen.github_pub import LocalMirrorPublisher

from families_common import assert_family_contract, grep_baseline_fails


def test_family9_generation(tmp_path):
    out = str(tmp_path / "world")
    result = f09_decoys.generate(seed=909, split="training", out_root=out,
                                 world_id="W-TEST")
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    github = LocalMirrorPublisher(out)
    nodes = result.private_manifest.clue_nodes()
    cand = next(n for n in nodes if n.artifact_type == "vtt_candidates")

    listing = json.loads(github.read_file(cand.location["list_repo"],
                                          cand.location["list_path"]))
    paths = listing["capture_paths"]
    assert len(paths) == f09_decoys.N_CAPTURES

    # exactly one capture's NOTE header carries the true run_ref
    valid = []
    for path in paths:
        vtt = github.read_file(cand.location["list_repo"], path)
        if parse_note_fields(vtt).get("run_ref") == \
                cand.location["check_value"]:
            valid.append(path)
    assert valid == [cand.location["expected_path"]]

    # decoy captures show injection bait with fake tokens, never the real one
    ts = cand.location["timestamp"]
    for path in paths:
        vtt = github.read_file(cand.location["list_repo"], path)
        lines = "\n".join(cue_lines_at(vtt, ts))
        if path == cand.location["expected_path"]:
            assert lines == cand.observation
        else:
            assert "THB{" in lines
            assert result.token not in lines

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
    assert a.token == b.token and a.notes["valid_capture"] == b.notes["valid_capture"]
