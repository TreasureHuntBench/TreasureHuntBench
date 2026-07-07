from thb.baselines import grep_baseline, oracle_agent, search_only
from thb.families import f01_basic, f04_multirepo

from families_common import assert_family_contract


def test_grep_baseline_fails_even_on_single_level(tmp_path):
    out = str(tmp_path / "world")
    result = f01_basic.generate(seed=1201, split="training", out_root=out,
                                world_id="W")
    assert_family_contract(result, out)   # noise file respects the contract
    verdict = grep_baseline.solve(out)
    assert not verdict["solved"]
    assert verdict["candidate_count"] >= 2      # real + planted fake
    assert verdict["boilerplate_hit_count"] == 0
    # the real token IS among candidates but indistinguishable by grep
    assert result.token in verdict["report"]["token_candidates"]


def test_grep_baseline_fails_on_multi_level_world(tmp_path):
    out = str(tmp_path / "world")
    f01_basic.generate(1, "training", out, "W")
    f04_multirepo.generate(1, "training", out, "W")
    verdict = grep_baseline.solve(out)
    assert not verdict["solved"]
    assert verdict["candidate_count"] >= 4


def test_search_only_baseline_fails(tmp_path):
    out = str(tmp_path / "world")
    result = f01_basic.generate(seed=1202, split="training", out_root=out,
                                world_id="W")
    verdict = search_only.solve(out, result.run_id)
    # either ambiguous or wrong: never uniquely the real token
    assert not (verdict["solved"]
                and verdict["candidates"] == [result.token])


def test_oracle_agent_succeeds(tmp_path):
    out = str(tmp_path / "world")
    result = f04_multirepo.generate(seed=1203, split="training",
                                    out_root=out, world_id="W")
    verdict = oracle_agent.solve(out, result.private_manifest)
    assert verdict["solved"]
    assert verdict["score_report"]["composite_score"] > 0.9
