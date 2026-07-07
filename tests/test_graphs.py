import pytest

from thb.graphs.clue import ClueChain
from thb.graphs.skills import SkillGraph, skill_card_markdown
from thb.graphs.world import WorldGraph


def test_clue_chain_links_and_checks():
    chain = ClueChain("L1S1-7Q2K")
    n1 = chain.add("github_file", {"repo": "r", "path": "runbooks/s.md"},
                   "github", "points to records/x.md")
    n2 = chain.add("github_file", {"repo": "r", "path": "records/x.md"},
                   "github", "THB{...}")
    assert n1.next_node == n2.node_id
    assert chain.terminal is n2 and n2.next_node == ""
    assert chain.check() == []
    assert len(chain.to_dicts()) == 2


def test_clue_chain_detects_problems():
    chain = ClueChain("L1S1-XXXX")
    assert chain.check() == ["clue chain is empty"]
    chain.add("github_file", {"repo": "r", "path": "p"}, "github", "obs")
    chain.nodes[0].next_node = "dangling"
    assert any("next_node" in p for p in chain.check())


def test_world_graph_decoy_rules():
    wg = WorldGraph("W1", "L9", "L9S3", "training")
    wg.add("repo", {"repo": "real"})
    wg.add("repo", {"repo": "fake"}, decoy_status="decoy",
           invalid_rule="run_ref != L9S3-2D8")
    assert wg.check() == []
    assert len(wg.decoys()) == 1
    wg.add("repo", {"repo": "bad-decoy"}, decoy_status="decoy")
    assert any("invalid_rule" in p for p in wg.check())


def test_skill_graph_ordering():
    sg = SkillGraph()
    sg.introduce("get_gold_price", "L2S1", card_path="docs/L2S1_skill.md")
    sg.practice("get_gold_price", "L4S1")
    sg.require("get_gold_price", "L10S1")
    assert sg.check(["L2S1", "L4S1", "L10S1"]) == []
    # required before introduction -> problem
    assert sg.check(["L4S1", "L2S1", "L10S1"]) != []


def test_skill_graph_unknown_usage():
    sg = SkillGraph()
    with pytest.raises(ValueError):
        sg.practice("get_coldest_hour", "L3S2")
    with pytest.raises(ValueError):
        sg.introduce("not_a_known_skill", "L1S1")


def test_skill_card_contents():
    card = skill_card_markdown("get_gold_price",
                               inputs="date, currency=USD",
                               normalization="round to nearest integer")
    assert "Skill: get_gold_price" in card
    assert "round to nearest integer" in card
    assert "Store this skill" in card
