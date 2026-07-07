"""End-to-end: generate a full world, then walk the QC checklist."""
import json
import os

from thb.baselines import grep_baseline, oracle_agent, search_only
from thb.core.schemas import PrivateManifest
from thb.core.tokens import token_hash
from thb.eval.scoring import score_submission
from thb.core.schemas import Trace
from thb.validate.oracle import OracleSolver
from thb.worldgen import DEFAULT_PLAN, generate_world

from families_common import walk_public_texts


def test_full_world_qc(tmp_path):
    out = str(tmp_path / "world")
    private = str(tmp_path / "private")
    summaries = generate_world(seed=31337, split="training", out_root=out,
                               world_id="W-E2E", private_root=private,
                               validate=True)
    assert len(summaries) == len(DEFAULT_PLAN)
    assert all(s["validated"] for s in summaries)

    manifests = []
    for name in sorted(os.listdir(private)):
        with open(os.path.join(private, name), encoding="utf-8") as fh:
            manifests.append(PrivateManifest.from_json(fh.read()))
    assert len(manifests) == len(summaries)

    solver = OracleSolver(out)
    tokens = {}
    for manifest in manifests:
        # QC: oracle solver succeeds; exactly one final token per level
        token, events = solver.solve(manifest)
        tokens[manifest.task_id] = token
        assert token_hash(token) == manifest.final_token_hash

        # QC: skills used on the path are recorded in the skill graph
        used = {sid for n in manifest.clue_nodes() for sid in n.skill_ids}
        recorded = {s.skill_id for s in manifest.skills()}
        assert used <= recorded, manifest.task_id

        # QC: oracle-agent baseline scores it end to end
        verdict = oracle_agent.solve(out, manifest)
        assert verdict["solved"], manifest.task_id

        # QC: answer-without-trace is caught
        bare = Trace(task_id=manifest.task_id, agent_id="x", model_id="x",
                     final_submission=token, events=[])
        r = score_submission(bare, manifest)
        assert r["metrics"]["trace_plausibility_score"] <= 0.2

    # QC: all final tokens unique across the world
    assert len(set(tokens.values())) == len(tokens)

    # QC: grep and search-only baselines cannot solve the world
    grep_verdict = grep_baseline.solve(out)
    assert not grep_verdict["solved"]
    assert grep_verdict["boilerplate_hit_count"] == 0
    for manifest in manifests:
        so = search_only.solve(out, manifest.run_id)
        assert not (so["solved"]
                    and so["candidates"] == [tokens[manifest.task_id]])

    # QC: private data is fully outside the public tree
    private_markers = [m.final_token_hash for m in manifests]
    for path, text in walk_public_texts(out):
        for marker in private_markers:
            assert marker not in text, path

    # QC: public manifests exist for every task and disclose no answers
    for manifest in manifests:
        pm_path = os.path.join(out, "tasks", manifest.task_id,
                               "public_manifest.json")
        with open(pm_path, encoding="utf-8") as fh:
            pm = json.load(fh)
        assert pm["answer_format"] == "THB{...}"
        assert tokens[manifest.task_id] not in json.dumps(pm)

    # QC: world reproducibility — same seed regenerates identical tokens
    out2 = str(tmp_path / "world2")
    private2 = str(tmp_path / "private2")
    generate_world(seed=31337, split="training", out_root=out2,
                   world_id="W-E2E", private_root=private2, validate=False)
    for name in sorted(os.listdir(private2)):
        with open(os.path.join(private2, name), encoding="utf-8") as fh:
            again = PrivateManifest.from_json(fh.read())
        assert again.final_token_hash == next(
            m.final_token_hash for m in manifests
            if m.task_id == again.task_id)
