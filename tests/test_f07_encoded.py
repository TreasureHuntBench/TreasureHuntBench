from thb.artifacts.captures import parse_upload_log_titles
from thb.artifacts.encodings import acrostic_decode, caesar_decode
from thb.families import f07_encoded
from thb.gen.github_pub import LocalMirrorPublisher

from families_common import assert_family_contract, grep_baseline_fails


def test_family7_generation(tmp_path):
    out = str(tmp_path / "world")
    result = f07_encoded.generate(seed=707, split="training", out_root=out,
                                  world_id="W-TEST")
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    github = LocalMirrorPublisher(out)
    nodes = result.private_manifest.clue_nodes()
    log_node = next(n for n in nodes if n.artifact_type == "titles_list")

    # decoding the last five titles' first characters yields the tag
    titles = parse_upload_log_titles(
        github.read_file(log_node.location["repo"],
                         log_node.location["path"]))
    last5 = titles[-log_node.location["last_n"]:]
    raw = acrostic_decode(last5)
    decoded = caesar_decode(raw, log_node.location["shift"])
    assert decoded == log_node.observation
    assert raw != decoded  # the shift is not a no-op

    # the decoded tag names the repo and its route document
    route_node = nodes[2]
    assert decoded in route_node.location["repo"]
    assert route_node.location["path"] == "packets/%s_route.md" % decoded
    route = github.read_file(route_node.location["repo"],
                             route_node.location["path"])
    assert nodes[3].location["path"] in route

    terminal = nodes[3]
    assert github.read_file(terminal.location["repo"],
                            terminal.location["path"]).strip() == result.token


def test_family7_deterministic(tmp_path):
    a = f07_encoded.generate(41, "training", str(tmp_path / "a"), "W")
    b = f07_encoded.generate(41, "training", str(tmp_path / "b"), "W")
    assert a.token == b.token and a.run_id == b.run_id
