import pytest

from thb.families import f08_memory
from thb.gen.github_pub import LocalMirrorPublisher
from thb.graphs.skills import SkillGraph

from families_common import assert_family_contract, grep_baseline_fails


def _world(tmp_path, seed=808):
    out = str(tmp_path / "world")
    skills = SkillGraph()
    memory = {}
    r1 = f08_memory.generate(seed, "training", out, "W-TEST", sub_num=1,
                             skill_graph=skills, world_memory=memory)
    r2 = f08_memory.generate(seed, "training", out, "W-TEST", sub_num=2,
                             skill_graph=skills, world_memory=memory)
    return out, r1, r2, skills, memory


def test_family8_both_sublevels(tmp_path):
    out, r1, r2, skills, memory = _world(tmp_path)
    for result in (r1, r2):
        assert_family_contract(result, out)
        grep_baseline_fails(result, out)
    assert r1.token != r2.token

    github = LocalMirrorPublisher(out)

    # sub-level 1 defines the mappings; sub-level 2's start uses the terms
    terms = memory["L8_mappings"]["terms"]
    intro_doc = github.read_file(r1.start_repo, r1.start_path)
    for term in terms.values():
        assert term in intro_doc
    transfer_doc = github.read_file(r2.start_repo, r2.start_path)
    assert terms["weather_source"] in transfer_doc
    assert terms["video"] in transfer_doc
    # meanings are NOT redefined in sub-level 2
    assert "approved historical-weather source" not in transfer_doc

    # git history: the payload is only in commits before migration-complete
    nodes = r2.private_manifest.clue_nodes()
    hist_node = next(n for n in nodes if n.artifact_type == "git_history")
    history = github.history(hist_node.location["repo"])["main"]
    messages = [h["message"] for h in history]
    idx = messages.index(hist_node.location["before_message"])
    before = history[idx - 1]["files"][hist_node.location["path"]]
    assert nodes[-1].location["path"] in before        # payload routes on
    at_head = github.read_file(hist_node.location["repo"],
                               hist_node.location["path"])
    assert nodes[-1].location["path"] not in at_head   # scrubbed at head

    # skill graph ordering is respected
    assert skills.check([r1.run_id.split("-")[0],
                         r2.run_id.split("-")[0]]) == []


def test_family8_sub2_requires_memory(tmp_path):
    with pytest.raises(ValueError):
        f08_memory.generate(1, "training", str(tmp_path / "w"), "W",
                            sub_num=2, world_memory={})


def test_family8_terms_rotate_across_seeds(tmp_path):
    _, r1a, _, _, ma = _world(tmp_path / "a", seed=1)
    _, r1b, _, _, mb = _world(tmp_path / "b", seed=2)
    assert ma["L8_mappings"]["terms"] != mb["L8_mappings"]["terms"]
