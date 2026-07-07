from thb.artifacts.captures import cue_lines_at, parse_note_fields
from thb.families import f05_youtube
from thb.gen.github_pub import LocalMirrorPublisher

from families_common import assert_family_contract, grep_baseline_fails


def test_family5_generation(tmp_path):
    out = str(tmp_path / "world")
    result = f05_youtube.generate(seed=505, split="training", out_root=out,
                                  world_id="W-TEST")
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    github = LocalMirrorPublisher(out)
    nodes = result.private_manifest.clue_nodes()
    cap_node = next(n for n in nodes if n.artifact_type == "vtt_timestamp")

    # the start doc references the capture file path
    assert nodes[0].observation == cap_node.location["path"]

    # the clue lines appear exactly at the weather-derived timestamp
    vtt = github.read_file(cap_node.location["repo"],
                           cap_node.location["path"])
    ts = cap_node.location["timestamp"]
    lines = cue_lines_at(vtt, ts)
    assert "\n".join(lines) == cap_node.observation
    assert any(line.startswith("repository=") for line in lines)

    # one second earlier the clue is NOT visible (unless hour is 00)
    seconds = int(ts.split(":")[1])
    if seconds > 0:
        assert cue_lines_at(vtt, "00:%02d" % (seconds - 1)) != lines

    # NOTE header carries the run ref
    assert parse_note_fields(vtt)["run_ref"] == result.run_id

    terminal = nodes[-1]
    assert github.read_file(terminal.location["repo"],
                            terminal.location["path"]).strip() == result.token


def test_family5_deterministic(tmp_path):
    a = f05_youtube.generate(21, "training", str(tmp_path / "a"), "W")
    b = f05_youtube.generate(21, "training", str(tmp_path / "b"), "W")
    assert a.token == b.token and a.run_id == b.run_id
