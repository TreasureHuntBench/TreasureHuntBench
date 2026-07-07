from thb.families import f06_multilingual
from thb.gen.github_pub import LocalMirrorPublisher

from families_common import assert_family_contract, grep_baseline_fails


def test_family6_generation(tmp_path):
    out = str(tmp_path / "world")
    result = f06_multilingual.generate(seed=606, split="training",
                                       out_root=out, world_id="W-TEST")
    assert_family_contract(result, out)
    grep_baseline_fails(result, out)

    github = LocalMirrorPublisher(out)
    nodes = result.private_manifest.clue_nodes()

    # start document is German and carries the date verbatim
    de_doc = github.read_file(nodes[0].location["repo"],
                              nodes[0].location["path"])
    assert "Goldpreisquelle" in de_doc or "Übersetze" in de_doc
    assert nodes[1].location["query"]["date"] in de_doc

    # gold value names the branch; the Arabic doc lives only on that branch
    gold_int = nodes[1].observation
    branch_node = nodes[2]
    assert gold_int in branch_node.location["branch"]
    ar_doc = github.read_file(branch_node.location["repo"],
                              branch_node.location["path"],
                              branch=branch_node.location["branch"])
    assert "افتح" in ar_doc or "ترجم" in ar_doc  # Arabic operational text
    assert nodes[3].location["path"] in ar_doc   # terminal path verbatim
    import os
    assert not os.path.exists(github.file_path(
        branch_node.location["repo"], branch_node.location["path"], "main"))

    terminal = nodes[3]
    assert github.read_file(terminal.location["repo"],
                            terminal.location["path"],
                            branch=terminal.location["branch"]
                            ).strip() == result.token

    skills = {s.skill_id for s in result.private_manifest.skills()}
    assert "cross_lingual_clue_following" in skills


def test_family6_deterministic(tmp_path):
    a = f06_multilingual.generate(31, "training", str(tmp_path / "a"), "W")
    b = f06_multilingual.generate(31, "training", str(tmp_path / "b"), "W")
    assert a.token == b.token and a.run_id == b.run_id
