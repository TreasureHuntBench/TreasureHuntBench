import json

from thb.families import f05_youtube
from thb.gen.github_pub import LocalMirrorPublisher
from thb.gen.youtube_pub import YouTubeMirror

from families_common import assert_family_contract, grep_baseline_fails


def test_family5_generation(tmp_path):
    out = str(tmp_path / "world")
    result = f05_youtube.generate(seed=505, split="training", out_root=out,
                                  world_id="W-TEST")
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    github = LocalMirrorPublisher(out)
    mirror = YouTubeMirror(out)
    nodes = result.private_manifest.clue_nodes()
    video_node = next(n for n in nodes
                      if n.artifact_type == "youtube_timestamp")

    # the reference file in the start repo points at the mirrored video
    ref_path = nodes[0].observation
    ref = json.loads(github.read_file(nodes[0].location["repo"], ref_path))
    assert ref["video_ref"] == video_node.location["video_ref"]
    assert ref["channel"] == "@TreasureHuntBench"

    # the clue text appears exactly at the weather-derived timestamp
    ts = video_node.location["timestamp"]
    lines = mirror.text_at(video_node.location["video_ref"], ts)
    assert "\n".join(lines) == video_node.observation
    assert any(line.startswith("repository=") for line in lines)

    # one second earlier the clue is NOT visible (unless hour is 00)
    seconds = int(ts.split(":")[1])
    if seconds > 0:
        earlier = "00:%02d" % (seconds - 1)
        assert mirror.text_at(video_node.location["video_ref"],
                              earlier) != lines

    # unlisted by default and tagged with the run ref
    meta = mirror.metadata(video_node.location["video_ref"])
    assert meta["privacy"] == "unlisted"
    assert "run_ref=%s" % result.run_id in meta["description"]

    terminal = nodes[-1]
    assert github.read_file(terminal.location["repo"],
                            terminal.location["path"]).strip() == result.token


def test_family5_deterministic(tmp_path):
    a = f05_youtube.generate(21, "training", str(tmp_path / "a"), "W")
    b = f05_youtube.generate(21, "training", str(tmp_path / "b"), "W")
    assert a.token == b.token and a.run_id == b.run_id
