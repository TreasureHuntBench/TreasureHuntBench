from thb.families import f01_basic
from thb.gen.github_pub import LocalMirrorPublisher

from families_common import assert_family_contract, grep_baseline_fails


def test_family1_generation(tmp_path):
    out = str(tmp_path / "world")
    result = f01_basic.generate(seed=101, split="training", out_root=out,
                                world_id="W-TEST")
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    # manual walk of the intended path recovers the token
    github = LocalMirrorPublisher(out)
    nodes = result.private_manifest.clue_nodes()
    start = github.read_file(nodes[0].location["repo"],
                             nodes[0].location["path"])
    assert nodes[0].observation in start          # middle path referenced
    middle = github.read_file(nodes[1].location["repo"],
                              nodes[1].location["path"])
    for part in nodes[1].observation.split():
        assert part in middle                     # second repo + terminal path
    terminal = github.read_file(nodes[2].location["repo"],
                                nodes[2].location["path"])
    assert terminal.strip() == result.token


def test_family1_deterministic(tmp_path):
    a = f01_basic.generate(101, "training", str(tmp_path / "a"), "W")
    b = f01_basic.generate(101, "training", str(tmp_path / "b"), "W")
    assert a.token == b.token
    assert a.run_id == b.run_id
    assert a.start_repo == b.start_repo
    c = f01_basic.generate(102, "training", str(tmp_path / "c"), "W")
    assert c.token != a.token and c.start_repo != a.start_repo
