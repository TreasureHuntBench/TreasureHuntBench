import csv
import io

from thb.core.cache import SourceCache
from thb.families import f02_website
from thb.gen.github_pub import LocalMirrorPublisher

from families_common import assert_family_contract, grep_baseline_fails


def test_family2_generation(tmp_path):
    out = str(tmp_path / "world")
    result = f02_website.generate(seed=202, split="training", out_root=out,
                                  world_id="W-TEST")
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    nodes = result.private_manifest.clue_nodes()
    types = [n.artifact_type for n in nodes]
    assert types == ["github_file", "api_value", "csv_row", "github_file",
                     "api_value", "terminal"]

    github = LocalMirrorPublisher(out)
    cache = SourceCache(out + "/cache")

    # every api_value node has a cache entry with citation
    for node in nodes:
        if node.artifact_type == "api_value":
            entry = cache.get(node.source_cache_id)
            assert entry is not None and entry.citation
            assert entry.normalized_value == node.observation

    # the QID row in the CSV routes to the skill doc
    qid_node, row_node = nodes[1], nodes[2]
    table = github.read_file(row_node.location["repo"],
                             row_node.location["path"])
    rows = {r["item_id"]: r["document"]
            for r in csv.DictReader(io.StringIO(table))}
    assert rows[qid_node.observation] == nodes[3].location["path"]

    # skill doc introduces get_gold_price and the gold key names the repo
    skill_doc = github.read_file(nodes[3].location["repo"],
                                 nodes[3].location["path"])
    assert "Skill: get_gold_price" in skill_doc
    gold_int = nodes[4].observation
    assert "_%s_" % gold_int in nodes[5].location["repo"]
    assert github.read_file(nodes[5].location["repo"],
                            nodes[5].location["path"]).strip() == result.token

    # skill graph records the introduction
    skills = {s.skill_id: s for s in result.private_manifest.skills()}
    assert skills["get_gold_price"].introduced_in == "L2S1"


def test_family2_deterministic(tmp_path):
    a = f02_website.generate(7, "training", str(tmp_path / "a"), "W")
    b = f02_website.generate(7, "training", str(tmp_path / "b"), "W")
    assert a.token == b.token and a.start_repo == b.start_repo
