import os

import pytest

from thb.families import (f01_basic, f02_website, f03_api, f04_multirepo,
                          f05_youtube, f06_multilingual, f07_encoded,
                          f08_memory, f09_decoys, f10_grand)
from thb.graphs.skills import SkillGraph
from thb.validate.leakage import scan_level
from thb.validate.one_answer import validate_one_answer
from thb.validate.oracle import OracleError, OracleSolver


def _generate_all(tmp_path, seed=2024):
    out = str(tmp_path / "world")
    skills = SkillGraph()
    memory = {}
    results = []
    for module, kwargs in [
            (f01_basic, {}), (f02_website, {}), (f03_api, {}),
            (f04_multirepo, {}), (f05_youtube, {}), (f06_multilingual, {}),
            (f07_encoded, {}), (f08_memory, {"sub_num": 1}),
            (f08_memory, {"sub_num": 2}), (f09_decoys, {}),
            (f10_grand, {})]:
        results.append(module.generate(seed, "training", out, "W-VAL",
                                       skill_graph=skills,
                                       world_memory=memory, **kwargs))
    return out, results


def test_oracle_solves_every_family(tmp_path):
    out, results = _generate_all(tmp_path)
    solver = OracleSolver(out)
    for result in results:
        token, events = solver.solve(result.private_manifest)
        assert token == result.token, result.task_id
        assert events, result.task_id
        tools = {e["tool"] for e in events}
        assert any(t.startswith("github") for t in tools)


def test_leakage_scanner_passes_generated_levels(tmp_path):
    out, results = _generate_all(tmp_path)
    for result in results:
        report = scan_level(out, result.private_manifest)
        assert report["ok"], (result.task_id, report["violations"])


def test_one_answer_validator_passes(tmp_path):
    out, results = _generate_all(tmp_path)
    for result in results:
        report = validate_one_answer(out, result.private_manifest)
        assert report["ok"], (result.task_id, report["problems"])


def test_oracle_rejects_tampered_token(tmp_path):
    out = str(tmp_path / "world")
    result = f01_basic.generate(5, "training", out, "W")
    terminal = result.private_manifest.clue_nodes()[-1]
    path = os.path.join(out, "github", terminal.location["repo"],
                        "branches/main", terminal.location["path"])
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("THB{tamperedtamperedtampered}\n")
    with pytest.raises(OracleError):
        OracleSolver(out).solve(result.private_manifest)


def test_leakage_scanner_catches_token_exposure(tmp_path):
    out = str(tmp_path / "world")
    result = f01_basic.generate(6, "training", out, "W")
    # leak the token into an unrelated public file
    leak = os.path.join(out, "github", result.start_repo,
                        "branches/main/notes/leak.md")
    os.makedirs(os.path.dirname(leak), exist_ok=True)
    with open(leak, "w", encoding="utf-8") as fh:
        fh.write("value: %s\n" % result.token)
    report = scan_level(out, result.private_manifest)
    assert not report["ok"]
    assert any("token exposed" in v for v in report["violations"])


def test_leakage_scanner_catches_boilerplate(tmp_path):
    out = str(tmp_path / "world")
    result = f01_basic.generate(7, "training", out, "W")
    bad = os.path.join(out, "github", result.start_repo,
                       "branches/main/notes/hint.md")
    os.makedirs(os.path.dirname(bad), exist_ok=True)
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("The next clue is in the other repo.\n")
    report = scan_level(out, result.private_manifest)
    assert not report["ok"]


def test_one_answer_rejects_duplicate_valid_candidate(tmp_path):
    out = str(tmp_path / "world")
    result = f04_multirepo.generate(8, "training", out, "W")
    search = next(n for n in result.private_manifest.clue_nodes()
                  if n.artifact_type == "github_repo_search")
    # forge a second candidate that also passes the run_id check
    other = [r for r in os.listdir(os.path.join(out, "github"))
             if r != search.location["expected_repo"]
             and r.startswith(search.location["pattern"].split("*")[0])][0]
    forged = os.path.join(out, "github", other, "branches/main",
                          search.location["check_path"].format(repo=other))
    with open(forged, encoding="utf-8") as fh:
        text = fh.read()
    import re
    text = re.sub(r"run_id: \S+", "run_id: %s"
                  % search.location["check_value"], text)
    with open(forged, "w", encoding="utf-8") as fh:
        fh.write(text)
    report = validate_one_answer(out, result.private_manifest)
    assert not report["ok"]
